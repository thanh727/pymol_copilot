"""
Unit tests for the autonomous AgentController loop.
"""

import json
import unittest
from unittest.mock import MagicMock, patch
from pymol_ai_copilot.agent.controller import AgentController
from pymol_ai_copilot.agent.ollama_client import OllamaConnectionError
from pymol_ai_copilot.agent.tool_registry import GLOBAL_REGISTRY
from pymol_ai_copilot.agent.workflow_engine import GLOBAL_WORKFLOW_REGISTRY
from pymol_ai_copilot.config import CONFIG
from pymol_ai_copilot.pymol_bridge.version import get_pymol_version


class _FlakyRegistry:
    """Registry stub that returns a scripted sequence of results."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def execute(self, name, arguments):
        self.calls += 1
        return self.results.pop(0)


class _ContactFallbackRegistry:
    """Registry stub exposing a successful ligand-interaction analysis."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def get_ollama_tools(self, subset=None):
        return []

    def get(self, name):
        if name in ("analyze_ligand_interactions", "find_nearby_residues"):
            return {"name": name}
        return None

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return self.result


class _RoutedContactRegistry:
    """Registry stub returning a different result per tool name."""

    def __init__(self, results):
        self.results = results
        self.calls = []

    def get_ollama_tools(self, subset=None):
        return []

    def get(self, name):
        return {"name": name} if name in self.results else None

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return self.results[name]


class _SequencedRegistry:
    """Registry stub returning scripted results in call order."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def get_ollama_tools(self, subset=None):
        return []

    def get(self, name):
        return {"name": name}

    def list_tools(self):
        return [MagicMock(name="placeholder")]

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return self.results.pop(0)


class TestAgentController(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.controller = AgentController(
            ollama_client=self.mock_client,
            registry=GLOBAL_REGISTRY,
            model_name="mock-model"
        )

    def test_single_turn_text_response(self):
        # LLM returns text directly without tool calls
        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": "PDB 1AKE is adenylate kinase with an open conformation.",
            "tool_calls": []
        }

        result = self.controller.run("Tell me about 1AKE", max_steps=3)
        self.assertTrue(result["success"])
        self.assertEqual(result["steps_count"], 1)
        self.assertIn("adenylate kinase", result["final_response"])

    def test_multi_step_tool_loop(self):
        # Step 1: Model calls list_objects
        # Step 2: Model returns final response
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "list_objects",
                        "arguments": {}
                    }
                ]
            },
            {
                "role": "assistant",
                "content": "I have listed the objects and found none currently loaded.",
                "tool_calls": []
            }
        ]

        events = []
        def callback(evt):
            events.append(evt["type"])

        result = self.controller.run("Check loaded objects", max_steps=4, step_callback=callback)
        self.assertTrue(result["success"])
        self.assertEqual(result["steps_count"], 2)
        self.assertIn("tool_start", events)
        self.assertIn("tool_result", events)
        self.assertIn("final_response", events)
        self.assertIn("listed the objects", result["final_response"])

    def test_cancellation(self):
        def on_step(event):
            if event.get("type") == "thinking_start":
                self.controller.cancel()

        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": "Stopping.",
            "tool_calls": []
        }
        result = self.controller.run("Test instruction", max_steps=3, step_callback=on_step)
        self.assertTrue(result["cancelled"])

    def test_new_run_after_cancellation_is_not_blocked(self):
        """A previous Stop must not permanently cancel the controller."""
        self.controller.cancel()
        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": "Fresh response.",
            "tool_calls": []
        }
        result = self.controller.run("New instruction", max_steps=1)
        self.assertFalse(result["cancelled"])
        self.assertTrue(result["success"])
        self.assertIn("Fresh response", result["final_response"])

    def test_transient_tool_failure_is_retried(self):
        registry = _FlakyRegistry([
            {"success": False, "error": "Connection reset by peer"},
            {"success": False, "error": "Request timed out"},
            {"success": True, "objects": []}
        ])
        controller = AgentController(
            ollama_client=self.mock_client,
            registry=registry,
            model_name="mock-model"
        )
        controller.TRANSIENT_BACKOFF_SECONDS = 0

        result = controller._execute_tool_with_retry("list_objects", {})

        self.assertTrue(result["success"])
        self.assertEqual(registry.calls, 3)

    def test_deterministic_tool_failure_is_not_retried(self):
        registry = _FlakyRegistry([
            {"success": False, "error": "Unsupported molecular file extension '.txt'"},
            {"success": True}
        ])
        controller = AgentController(
            ollama_client=self.mock_client,
            registry=registry,
            model_name="mock-model"
        )

        result = controller._execute_tool_with_retry("load_structure", {"file_path": "x.txt"})

        self.assertFalse(result["success"])
        self.assertEqual(registry.calls, 1)

    def test_transient_tool_failure_stops_after_bounded_retries(self):
        registry = _FlakyRegistry([
            {"success": False, "error": "Connection refused"},
            {"success": False, "error": "Connection refused"},
            {"success": False, "error": "Connection refused"}
        ])
        controller = AgentController(
            ollama_client=self.mock_client,
            registry=registry,
            model_name="mock-model"
        )
        controller.TRANSIENT_BACKOFF_SECONDS = 0

        result = controller._execute_tool_with_retry("fetch_structure", {"pdb_id": "1ubq"})

        self.assertFalse(result["success"])
        self.assertTrue(result["transient_exhausted"])
        self.assertEqual(registry.calls, 3)

    def test_workflow_tool_scope_is_enforced_at_execution(self):
        """Tools excluded from the matched workflow must be rejected, not executed."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF02")
        self.assertIsNotNone(wf)
        self.assertNotIn("fetch_structure", wf.required_capabilities)

        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_scope",
                    "name": "fetch_structure",
                    "arguments": {"pdb_id": "1ubq"}
                }]
            },
            {
                "role": "assistant",
                "content": "The requested tool is outside the current workflow scope.",
                "tool_calls": []
            }
        ]

        with patch(
            "pymol_ai_copilot.agent.controller.GLOBAL_WORKFLOW_REGISTRY.match_workflow",
            return_value=(wf, {}, 0.95)
        ):
            result = self.controller.run("Describe the loaded protein", max_steps=3)

        tr = result["steps"][0]["tool_results"][0]
        self.assertFalse(tr["result"]["success"])
        self.assertTrue(tr["result"].get("workflow_scope_violation"))
        self.assertIn("outside the approved capability scope", tr["result"]["error"])

    def test_workflow_nudges_model_to_execute_instead_of_describing(self):
        """A model that only restates a workflow plan must be pushed to call tools."""
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": (
                    "1. Discover Ligands: Identify bound organic ligands. "
                    "2. Analyze Pocket Contacts. 3. Visualize Pocket. "
                    "Which step would you like to run?"
                ),
                "tool_calls": []
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_objects",
                    "name": "list_objects",
                    "arguments": {}
                }]
            },
            {
                "role": "assistant",
                "content": "Inspected the session and executed the workflow.",
                "tool_calls": []
            }
        ]

        events = []
        result = self.controller.run(
            "Visualize Pocket: Render pocket sticks with dashed polar contacts and centered view.",
            max_steps=4,
            step_callback=lambda e: events.append(e["type"])
        )

        self.assertIn("execution_nudge", events)
        tools_called = [tr["tool"] for s in result["steps"] for tr in s["tool_results"]]
        self.assertIn("list_objects", tools_called)
        self.assertIn("executed the workflow", result["final_response"])

    def test_failed_tool_call_nudges_retry_with_corrected_arguments(self):
        """After a failed selection the model must retry, not ask the user to guess."""
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_bad",
                    "name": "find_nearby_residues",
                    "arguments": {"target_selection": "resn SUL", "cutoff": 4}
                }]
            },
            {
                "role": "assistant",
                "content": "I could not find SUL. Which residue name should I use?",
                "tool_calls": []
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_inspect",
                    "name": "list_objects",
                    "arguments": {}
                }]
            },
            {
                "role": "assistant",
                "content": "Retried with a corrected selection.",
                "tool_calls": []
            }
        ]

        events = []
        result = self.controller.run(
            "visualize SO4 binding residues",
            max_steps=5,
            step_callback=lambda e: events.append(e["type"])
        )

        self.assertIn("failure_nudge", events)
        tools_called = [tr["tool"] for s in result["steps"] for tr in s["tool_results"]]
        self.assertEqual(tools_called[:2], ["find_nearby_residues", "list_objects"])
        self.assertIn("corrected selection", result["final_response"])

    def test_fabricated_results_without_tool_calls_are_blocked(self):
        """An actionable request answered without tools must be sent back for verification."""
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "Các residue tương tác là ASP 100, ASP 102 và ASP 104.",
                "tool_calls": []
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_verify",
                    "name": "list_objects",
                    "arguments": {}
                }]
            },
            {
                "role": "assistant",
                "content": "Verified against the live session.",
                "tool_calls": []
            }
        ]

        events = []
        result = self.controller.run(
            "xác định các residues tương tác với SO4",
            max_steps=4,
            step_callback=lambda e: events.append(e["type"])
        )

        self.assertIn("truthfulness_nudge", events)
        tools_called = [tr["tool"] for s in result["steps"] for tr in s["tool_results"]]
        self.assertEqual(tools_called, ["list_objects"])
        self.assertIn("Verified against", result["final_response"])

    def test_conversational_answer_without_tools_is_allowed(self):
        """Non-actionable questions must not be forced into tool execution."""
        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": "RMSD is the root-mean-square deviation between aligned atoms.",
            "tool_calls": []
        }

        events = []
        result = self.controller.run(
            "What does RMSD mean?",
            max_steps=2,
            step_callback=lambda e: events.append(e["type"])
        )

        self.assertNotIn("truthfulness_nudge", events)
        self.assertEqual(result["steps_count"], 1)
        self.assertIn("root-mean-square", result["final_response"])

    def test_plan_only_contact_answer_falls_back_to_grounded_analysis(self):
        """A plan-only answer after the truthfulness nudge must still produce data."""
        plan = (
            "Để xác định các residue quan trọng, bạn có thể thực hiện các bước sau:\n"
            "1. find_nearby_residues(target_selection='resn SO4')\n"
            "2. analyze_ligand_interactions(object_name='5jnm')\n"
        )
        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": plan,
            "tool_calls": []
        }

        analysis = {
            "success": True,
            "object": "5jnm",
            "ligand_resn": "SO4",
            "cutoff_angstrom": 5.0,
            "contacting_residues_count": 2,
            "polar_contacts_count": 3,
            "contacts": [
                {
                    "residue_name": "ARG",
                    "residue_number": "283",
                    "chain": "A",
                    "min_distance_angstrom": 2.544,
                    "contact_type": "polar",
                    "polar_contacts": [
                        {"residue_atom": "NH1", "ligand_atom": "O4", "distance_angstrom": 2.544}
                    ]
                },
                {
                    "residue_name": "LEU",
                    "residue_number": "155",
                    "chain": "A",
                    "min_distance_angstrom": 3.821,
                    "contact_type": "hydrophobic_or_vdw",
                    "polar_contacts": []
                }
            ]
        }
        registry = _ContactFallbackRegistry(analysis)

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        events = []
        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "liệt kê các residue quan trọng tương tác với SO4 và loại tương tác",
                max_steps=4,
                step_callback=lambda e: events.append(e["type"])
            )

        self.assertIn("truthfulness_nudge", events)
        self.assertIn("tool_start", events)
        self.assertEqual(registry.calls[0][0], "analyze_ligand_interactions")
        self.assertEqual(registry.calls[0][1]["ligand_resn"], "SO4")
        self.assertEqual(registry.calls[0][1]["object_name"], "5jnm")
        self.assertIn("ARG283", result["final_response"])
        self.assertIn("LEU155", result["final_response"])
        self.assertIn("polar", result["final_response"])
        tools_used = [tr["tool"] for s in result["steps"] for tr in s["tool_results"]]
        self.assertEqual(tools_used, ["analyze_ligand_interactions"])
        self.assertTrue(result["success"])

    def test_proximity_only_success_still_runs_typed_analysis(self):
        """When the user asks for contact types, proximity-only data is not enough."""
        proximity = {
            "success": True,
            "target_selection": "resn SO4",
            "residue_count": 2,
            "residues": [
                {"resn": "ARG", "resi": "283", "chain": "A"},
                {"resn": "LEU", "resi": "155", "chain": "A"}
            ],
            "per_instance": []
        }
        typed = {
            "success": True,
            "object": "5jnm",
            "ligand_resn": "SO4",
            "cutoff_angstrom": 4.0,
            "contacts": [
                {
                    "residue_name": "ARG",
                    "residue_number": "283",
                    "chain": "A",
                    "min_distance_angstrom": 2.544,
                    "contact_type": "polar",
                    "polar_contacts": [
                        {"residue_atom": "NH1", "ligand_atom": "O4", "distance_angstrom": 2.544}
                    ]
                },
                {
                    "residue_name": "LEU",
                    "residue_number": "155",
                    "chain": "A",
                    "min_distance_angstrom": 3.821,
                    "contact_type": "hydrophobic_or_vdw",
                    "polar_contacts": []
                }
            ]
        }
        registry = _RoutedContactRegistry({
            "find_nearby_residues": proximity,
            "analyze_ligand_interactions": typed
        })
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_near",
                    "name": "find_nearby_residues",
                    "arguments": {"target_selection": "resn SO4", "cutoff": 5.0}
                }]
            },
            {
                "role": "assistant",
                "content": "LEU155 tạo nhóm carboxyl nên là liên kết điện cực.",
                "tool_calls": []
            }
        ]

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "liệt kê các residue quan trọng tương tác với SO4 và loại tương tác",
                max_steps=4
            )

        tools_used = [tr["tool"] for s in result["steps"] for tr in s["tool_results"]]
        self.assertEqual(
            tools_used,
            ["find_nearby_residues", "analyze_ligand_interactions"]
        )
        self.assertIn("ARG283", result["final_response"])
        self.assertIn("kỵ nước", result["final_response"])
        self.assertNotIn("carboxyl", result["final_response"])

    def test_per_instance_request_overrides_merged_answer(self):
        """A merged proximity answer must be replaced by one group per ligand/ion."""
        per_instance = [
            {
                "target": {"resn": "SO4", "resi": "401", "chain": "A"},
                "residue_count": 2,
                "residues": [
                    {"resn": "ASN", "resi": "119", "chain": "A"},
                    {"resn": "ARG", "resi": "287", "chain": "A"}
                ]
            },
            {
                "target": {"resn": "SO4", "resi": "402", "chain": "A"},
                "residue_count": 2,
                "residues": [
                    {"resn": "LEU", "resi": "155", "chain": "A"},
                    {"resn": "ARG", "resi": "283", "chain": "A"}
                ]
            },
            {
                "target": {"resn": "SO4", "resi": "403", "chain": "A"},
                "residue_count": 1,
                "residues": [
                    {"resn": "SER", "resi": "272", "chain": "A"}
                ]
            }
        ]
        proximity = {
            "success": True,
            "target_selection": "resn SO4",
            "cutoff_angstroms": 5.0,
            "target_count": 3,
            "residues": [],
            "per_instance": per_instance
        }
        registry = _RoutedContactRegistry({"find_nearby_residues": proximity})
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_near",
                    "name": "find_nearby_residues",
                    "arguments": {"target_selection": "resn SO4", "cutoff": 5.0}
                }]
            },
            {
                "role": "assistant",
                "content": "Đã hiển thị các residue tương tác với SO4 bằng sticks.",
                "tool_calls": []
            }
        ]

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "chúng ta có 3 phân tử SO4, tìm tất cả các residues tương tác với từng phân tử SO4",
                max_steps=4
            )

        response = result["final_response"]
        for identifier in ("401", "402", "403"):
            self.assertIn(identifier, response)
        self.assertIn("ASN119", response)
        self.assertIn("SER272", response)
        # The existing proximity result is reused; no extra analysis is needed.
        self.assertEqual([name for name, _ in registry.calls], ["find_nearby_residues"])

    def test_per_instance_request_with_types_runs_typed_analysis(self):
        """Per-instance contact-type requests must analyse every instance separately."""
        per_instance = [
            {
                "target": {"resn": "SO4", "resi": "401", "chain": "A"},
                "residue_count": 1,
                "residues": [{"resn": "ARG", "resi": "283", "chain": "A"}]
            },
            {
                "target": {"resn": "SO4", "resi": "402", "chain": "A"},
                "residue_count": 1,
                "residues": [{"resn": "LEU", "resi": "155", "chain": "A"}]
            }
        ]
        proximity = {
            "success": True,
            "cutoff_angstroms": 4.0,
            "target_count": 2,
            "residues": [],
            "per_instance": per_instance
        }
        typed = {
            "success": True,
            "contacts": [{
                "residue_name": "ARG",
                "residue_number": "283",
                "chain": "A",
                "min_distance_angstrom": 2.544,
                "contact_type": "polar",
                "polar_contacts": []
            }]
        }
        registry = _RoutedContactRegistry({
            "find_nearby_residues": proximity,
            "analyze_ligand_interactions": typed
        })
        plan = "1. find_nearby_residues\n2. analyze_ligand_interactions"
        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": plan,
            "tool_calls": []
        }

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "liệt kê loại tương tác của từng phân tử SO4",
                max_steps=4
            )

        response = result["final_response"]
        self.assertIn("401", response)
        self.assertIn("402", response)
        self.assertIn("polar", response)
        analyzed = [args for name, args in registry.calls if name == "analyze_ligand_interactions"]
        self.assertEqual(len(analyzed), 2)
        self.assertEqual({args["ligand_resi"] for args in analyzed}, {"401", "402"})
        self.assertNotIn("1. find_nearby", response)

    def test_per_instance_typed_answer_requires_per_instance_analysis(self):
        """Naming the instances is not enough when contact types were requested."""
        per_instance = [
            {
                "target": {"resn": "SO4", "resi": "401", "chain": "A"},
                "residue_count": 1,
                "residues": [{"resn": "ARG", "resi": "283", "chain": "A"}]
            },
            {
                "target": {"resn": "SO4", "resi": "402", "chain": "A"},
                "residue_count": 1,
                "residues": [{"resn": "LEU", "resi": "155", "chain": "A"}]
            }
        ]
        proximity = {
            "success": True,
            "cutoff_angstroms": 4.0,
            "target_count": 2,
            "residues": [],
            "per_instance": per_instance
        }
        typed = {
            "success": True,
            "contacts": [{
                "residue_name": "ARG",
                "residue_number": "283",
                "chain": "A",
                "min_distance_angstrom": 2.544,
                "contact_type": "polar",
                "polar_contacts": []
            }]
        }
        registry = _RoutedContactRegistry({
            "find_nearby_residues": proximity,
            "analyze_ligand_interactions": typed
        })
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_near",
                    "name": "find_nearby_residues",
                    "arguments": {"target_selection": "resn SO4", "cutoff": 4.0}
                }]
            },
            {
                "role": "assistant",
                "content": "SO4 401 có hydrogen bond; SO4 402 cũng có hydrogen bond.",
                "tool_calls": []
            }
        ]

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "liệt kê loại tương tác của từng phân tử SO4",
                max_steps=4
            )

        analyzed = [args for name, args in registry.calls if name == "analyze_ligand_interactions"]
        self.assertEqual(len(analyzed), 2)
        self.assertEqual({args["ligand_resi"] for args in analyzed}, {"401", "402"})
        self.assertIn("polar", result["final_response"])
        self.assertNotIn("hydrogen bond", result["final_response"])

    def test_per_instance_detection_uses_word_boundaries(self):
        self.assertFalse(
            AgentController._wants_per_instance("teach me about residue contacts")
        )
        self.assertTrue(
            AgentController._wants_per_instance("residues for each SO4")
        )
        self.assertTrue(
            AgentController._wants_per_instance("residues tương tác với từng SO4")
        )

    def test_polar_pair_output_does_not_replace_residue_request(self):
        """A polar-pair tool result is insufficient when the user asked for residues."""
        polar = {
            "success": True,
            "distance_object": "ai_polar_contacts",
            "candidates_count": 37,
            "measured_distances_angstroms": [2.5, 2.6]
        }
        typed = {
            "success": True,
            "contacts": [{
                "residue_name": "ARG",
                "residue_number": "283",
                "chain": "A",
                "min_distance_angstrom": 2.544,
                "contact_type": "polar",
                "polar_contacts": []
            }]
        }
        registry = _RoutedContactRegistry({
            "find_polar_contact_candidates": polar,
            "analyze_ligand_interactions": typed
        })
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_polar",
                    "name": "find_polar_contact_candidates",
                    "arguments": {"selection1": "resn SO4", "selection2": "all"}
                }]
            },
            {
                "role": "assistant",
                "content": "Có 37 phân tử SO4 tương tác trong cấu trúc.",
                "tool_calls": []
            }
        ]

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "liệt kê các residue tương tác với SO4",
                max_steps=4
            )

        tools_used = [tr["tool"] for s in result["steps"] for tr in s["tool_results"]]
        self.assertEqual(
            tools_used,
            ["find_polar_contact_candidates", "analyze_ligand_interactions"]
        )
        self.assertIn("ARG283", result["final_response"])
        self.assertNotIn("37 phân tử", result["final_response"])

    def test_visualize_request_is_not_replaced_by_residue_table(self):
        """Pure visualization requests must keep the model's visual confirmation."""
        show = {"success": True, "shown": "sticks", "selection": "resn SO4", "atom_count": 15}
        registry = _RoutedContactRegistry({"show_representation": show})
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_show",
                    "name": "show_representation",
                    "arguments": {"representation": "sticks", "selection": "resn SO4"}
                }]
            },
            {
                "role": "assistant",
                "content": "Đã hiển thị các residue tương tác với SO4.",
                "tool_calls": []
            }
        ]

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "visualize SO4 binding residues",
                max_steps=4
            )

        self.assertEqual([name for name, _ in registry.calls], ["show_representation"])
        self.assertEqual(result["final_response"], "Đã hiển thị các residue tương tác với SO4.")

    def test_followup_pronoun_injects_last_successful_selection(self):
        """A follow-up like 'zoom in on it' must reuse the previous target."""
        registry = _RoutedContactRegistry({
            "zoom_selection": {
                "success": True,
                "zoomed": "model 5jnm and resn 'SO4'"
            }
        })
        controller = AgentController(
            ollama_client=self.mock_client,
            registry=registry,
            model_name="mock-model"
        )
        controller._last_focus = {
            "tool": "find_nearby_residues",
            "object": "5jnm",
            "selection": "model 5jnm and resn 'SO4'",
            "resn": "SO4",
            "resi": "401",
            "chain": "A",
        }
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_zoom",
                    "name": "zoom_selection",
                    "arguments": {"selection": "model 5jnm and resn 'SO4'"}
                }]
            },
            {
                "role": "assistant",
                "content": "Zoomed on the SO4 binding site.",
                "tool_calls": []
            }
        ]

        result = controller.run("zoom in on it", max_steps=2)

        first_messages = self.mock_client.chat.call_args_list[0].kwargs["messages"]
        system_prompt = first_messages[0]["content"]
        self.assertIn("Follow-up Context", system_prompt)
        self.assertIn("model 5jnm and resn 'SO4'", system_prompt)
        self.assertEqual(registry.calls[0][0], "zoom_selection")
        self.assertIn("Zoomed on the SO4", result["final_response"])

    def test_followup_without_focus_requests_clarification(self):
        """A dangling pronoun must not make the controller invent a target."""
        hint = self.controller._followup_focus_hint("zoom in on it")
        self.assertIn("Ask the user", hint)

        explicit = self.controller._followup_focus_hint(
            "Download PDB 1UBQ and display it."
        )
        self.assertEqual(explicit, "")

    def test_focus_tracks_only_successful_tool_targets(self):
        self.controller._update_followup_focus(
            "find_nearby_residues",
            {"target_selection": "model 5jnm and resn 'SO4'"},
            {
                "success": True,
                "target_selection": "model 5jnm and resn 'SO4'",
                "targets": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }
        )
        self.assertEqual(
            self.controller._last_focus["selection"],
            "model 5jnm and resn 'SO4'"
        )
        self.assertEqual(self.controller._last_focus["resn"], "SO4")

        previous = dict(self.controller._last_focus)
        self.controller._update_followup_focus(
            "color_selection",
            {"selection": "resn NOPE"},
            {"success": False, "error": "Selection matches 0 atoms"}
        )
        self.assertEqual(self.controller._last_focus, previous)

    def test_connection_error_gives_actionable_guidance(self):
        """An offline Ollama server must not produce a generic stack-trace message."""
        self.mock_client.chat.side_effect = OllamaConnectionError("Connection refused")

        result = self.controller.run("Show the protein as cartoon", max_steps=1)

        self.assertFalse(result["success"])
        self.assertIn("ollama serve", result["final_response"].lower())

    def test_duplicate_successful_tool_call_is_rejected(self):
        """Repeating an identical successful call must not loop forever."""
        registry = _SequencedRegistry([
            {"success": True, "shown": "sticks", "selection": "resn 'SO4'", "atom_count": 15},
            {"success": True, "hidden": "everything", "selection": "solvent"},
        ])
        show_args = {"representation": "sticks", "selection": "SO4"}
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_show_1",
                    "name": "show_representation",
                    "arguments": dict(show_args)
                }]
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_show_2",
                    "name": "show_representation",
                    "arguments": dict(show_args)
                }]
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_hide",
                    "name": "hide_representation",
                    "arguments": {"representation": "water", "selection": "all"}
                }]
            },
            {
                "role": "assistant",
                "content": "SO4 is shown and water is hidden.",
                "tool_calls": []
            }
        ]
        controller = AgentController(
            ollama_client=self.mock_client,
            registry=registry,
            model_name="mock-model"
        )

        result = controller.run(
            "show SO4 as sticks and hide all water",
            max_steps=4
        )

        self.assertEqual(len(registry.calls), 2)
        self.assertEqual(registry.calls[0][0], "show_representation")
        self.assertEqual(registry.calls[1][0], "hide_representation")

        duplicate = result["steps"][1]["tool_results"][0]["result"]
        self.assertFalse(duplicate["success"])
        self.assertTrue(duplicate["repeated_success"])
        self.assertIn("already succeeded", duplicate["error"])
        self.assertIn("water is hidden", result["final_response"])

    def test_label_request_is_executed_after_proximity_analysis(self):
        """A 'label the residues' request must actually label, not just describe."""
        proximity = {
            "success": True,
            "target_selection": "resn 'SO4'",
            "cutoff_angstroms": 4.0,
            "target_count": 1,
            "residue_count": 2,
            "residues": [
                {"resn": "ARG", "resi": "283", "chain": "A"},
                {"resn": "ASN", "resi": "119", "chain": "A"},
            ],
            "per_instance": [],
        }
        registry = _RoutedContactRegistry({
            "find_nearby_residues": proximity,
            "label_residues": {"success": True, "label_type": "resn_resi"},
        })
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_near",
                    "name": "find_nearby_residues",
                    "arguments": {"target_selection": "SO4", "cutoff": 4.0}
                }]
            },
            {
                "role": "assistant",
                "content": "The residues near SO4 are ARG283 and ASN119.",
                "tool_calls": []
            }
        ]

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "label the residues interacting with SO4",
                max_steps=3
            )

        labeled = [args for name, args in registry.calls if name == "label_residues"]
        self.assertEqual(len(labeled), 1)
        self.assertIn("chain 'A' and resi '283'", labeled[0]["selection"])
        self.assertIn("Labels added", result["final_response"])

    def test_label_request_is_executed_after_deterministic_fallback(self):
        """The deterministic contact fallback must also execute requested labels."""
        typed = {
            "success": True,
            "object": "5jnm",
            "ligand_resn": "SO4",
            "cutoff_angstrom": 4.0,
            "contacts": [
                {
                    "residue_name": "ARG",
                    "residue_number": "283",
                    "chain": "A",
                    "min_distance_angstrom": 2.544,
                    "contact_type": "polar",
                    "polar_contacts": [],
                },
                {
                    "residue_name": "ASN",
                    "residue_number": "119",
                    "chain": "A",
                    "min_distance_angstrom": 2.861,
                    "contact_type": "polar",
                    "polar_contacts": [],
                },
            ],
        }
        registry = _RoutedContactRegistry({
            "analyze_ligand_interactions": typed,
            "label_residues": {"success": True, "label_type": "resn_resi"},
        })
        self.mock_client.chat.side_effect = [
            {"role": "assistant", "content": "I will label them.", "tool_calls": []},
            {"role": "assistant", "content": "I will label them.", "tool_calls": []},
        ]

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: 5jnm loaded"
        context.inspector.get_loaded_objects.return_value = ["5jnm"]
        context.inspector.get_structure_summary.return_value = {
            "object_count": 1,
            "objects": [{
                "name": "5jnm",
                "ligands": [],
                "heteroatoms": [{"resn": "SO4", "resi": "401", "chain": "A"}]
            }],
            "named_selections": []
        }

        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "label the residues interacting with SO4",
                max_steps=3
            )

        labeled = [args for name, args in registry.calls if name == "label_residues"]
        self.assertEqual(len(labeled), 1)
        self.assertIn("chain 'A' and resi '283'", labeled[0]["selection"])
        self.assertIn("chain 'A' and resi '119'", labeled[0]["selection"])
        self.assertIn("Labels added", result["final_response"])

    def test_contact_fallback_skipped_without_session_ligand(self):
        """Conceptual/unspecified requests must not invent a ligand target."""
        plan = "Bạn cần chỉ rõ ligand nào trước khi tôi có thể phân tích."
        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": plan,
            "tool_calls": []
        }
        registry = _ContactFallbackRegistry({"success": True, "contacts": []})

        context = MagicMock()
        context.inspector.get_context_for_prompt.return_value = "PyMOL Context: empty"
        context.inspector.get_loaded_objects.return_value = []
        context.inspector.get_structure_summary.return_value = {
            "object_count": 0,
            "objects": [],
            "named_selections": []
        }

        events = []
        with patch("pymol_ai_copilot.agent.controller.GLOBAL_CONTEXT", context):
            controller = AgentController(
                ollama_client=self.mock_client,
                registry=registry,
                model_name="mock-model"
            )
            result = controller.run(
                "liệt kê các residue tương tác với ligand",
                max_steps=4,
                step_callback=lambda e: events.append(e["type"])
            )

        self.assertNotIn("tool_start", events)
        self.assertEqual(registry.calls, [])
        self.assertEqual(result["final_response"], plan)

    def test_conversation_history_is_bounded(self):
        """Long conversations must not grow the model context without limit."""
        original = CONFIG.max_history_messages
        CONFIG.max_history_messages = 4
        try:
            self.mock_client.chat.return_value = {
                "role": "assistant",
                "content": "ok",
                "tool_calls": []
            }
            for i in range(10):
                self.controller.run(f"question {i}", max_steps=1)

            self.assertLessEqual(len(self.controller.conversation_history), 4)
            self.assertEqual(self.controller.conversation_history[0]["role"], "user")
        finally:
            CONFIG.max_history_messages = original

    def test_large_tool_results_are_truncated_for_context(self):
        original = CONFIG.max_tool_result_chars
        CONFIG.max_tool_result_chars = 200
        try:
            payload = AgentController._serialize_tool_result({
                "success": True,
                "rows": ["x" * 1000]
            })
            parsed = json.loads(payload)
            self.assertTrue(parsed["truncated"])
            self.assertLessEqual(len(payload), 500)
            self.assertIn("rows", parsed["preview"])
        finally:
            CONFIG.max_tool_result_chars = original

    def test_provenance_uses_runtime_pymol_version(self):
        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": "done",
            "tool_calls": []
        }
        result = self.controller.run("hello", max_steps=1)
        self.assertEqual(result["provenance"]["pymol_version"], get_pymol_version())


if __name__ == "__main__":
    unittest.main()

