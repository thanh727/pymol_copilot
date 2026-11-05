# Installed PyMOL API inventory

- PyMOL: `3.1.0`
- Python: `3.14.3` (`/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/bin/python`)
- Public Python API / PML command entries: **488**
- PML command registry names: **312**
- Public callable cmd attributes: **440**

**Inventory is not a tool allowlist. All entries default to LLM-disallowed.**

## Category overview

| Category | Number of primary entries |
|---|---:|
| 01 Input, retrieval, files | 16 |
| 02 Object and session management | 19 |
| 03 Structure inspection | 25 |
| 04 Selection and atom queries | 10 |
| 05 Representation and color | 14 |
| 06 Camera and viewport | 17 |
| 07 Distances and geometry | 6 |
| 08 Structure alignment | 11 |
| 09 Surface and accessibility | 5 |
| 10 Editing and mutations | 23 |
| 11 Maps and volumetric | 12 |
| 12 States and trajectories | 3 |
| 13 Movies and scenes | 12 |
| 14 Rendering and figures | 6 |
| 15 Settings and configuration | 5 |
| 16 Crystallography and symmetry | 2 |
| 17 Command language and extension | 15 |
| 99 Uncategorized / review | 287 |

## Discovered commands and Python API

### 01 Input, retrieval, files

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `fetch` | Yes | Yes | I/O: allowlisted paths/network and collision checks | `(code, name='', state=0, finish=1, discrete=-1, multiplex=-2, zoom=-1, type='', async_=0, path='', file=None, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `get_cifstr` | Yes | No | read-only candidate: typed adapter required | `(selection='all', state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_pdbstr` | Yes | No | read-only candidate: typed adapter required | `(selection='all', state=-1, ref='', ref_state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_session` | Yes | No | I/O: allowlisted paths/network and collision checks | `(names='', partial=0, quiet=1, compress=-1, cache=-1, binary=-1, version=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load` | Yes | Yes | I/O: allowlisted paths/network and collision checks | `(filename, object='', state=0, format='', finish=1, discrete=-1, quiet=1, multiplex=None, zoom=-1, partial=0, mimic=1, object_props=None, atom_props=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_cgo` | Yes | No | mutation: approval or dedicated guarded workflow | `(*arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kw)` |
| `load_model` | Yes | No | mutation: approval or dedicated guarded workflow | `(*arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kw)` |
| `load_traj` | Yes | Yes | I/O: allowlisted paths/network and collision checks | `(filename, object='', state=1, format='', interval=1, average=1, start=1, stop=-1, max=-1, selection='all', image=1, shift='[0.0,0.0,0.0]', plugin='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mpng` | Yes | Yes | I/O: allowlisted paths/network and collision checks | `(prefix, first=0, last=0, preserve=0, modal=0, mode=-1, quiet=1, width=0, height=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `multifilesave` | Yes | Yes | I/O: allowlisted paths/network and collision checks | `(filename, selection='*', state=-1, format='', ref='', ref_state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `multisave` | Yes | Yes | I/O: allowlisted paths/network and collision checks | `(filename, pattern='all', state=-1, append=0, format='', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `png` | Yes | Yes | I/O: allowlisted paths/network and collision checks | `(filename, width=0, height=0, dpi=-1.0, ray=0, quiet=1, prior=0, format=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `read_molstr` | Yes | No | I/O: allowlisted paths/network and collision checks | `(molstr, name, state=0, finish=1, discrete=1, quiet=1, zoom=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `read_pdbstr` | Yes | No | I/O: allowlisted paths/network and collision checks | `(contents, oname, state=0, finish=1, discrete=0, quiet=1, zoom=-1, multiplex=-2, object_props=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `save` | Yes | Yes | I/O: allowlisted paths/network and collision checks | `(filename, selection='(all)', state=-1, format='', ref='', ref_state=-1, quiet=1, partial=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_session` | Yes | No | mutation: approval or dedicated guarded workflow | `(session, partial=0, quiet=1, cache=1, steal=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 02 Object and session management

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `copy` | Yes | Yes | manual review: NOT auto-authorized | `(target, source, zoom=-1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `count_states` | Yes | Yes | read-only candidate: typed adapter required | `(selection='(all)', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `create` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(name, selection, source_state=0, target_state=0, discrete=0, zoom=-1, quiet=1, singletons=0, extract=None, copy_properties=False, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `delete` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(name, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `disable` | Yes | Yes | manual review: NOT auto-authorized | `(name='all', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `enable` | Yes | Yes | manual review: NOT auto-authorized | `(name='all', parents=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `extract` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(name, selection, *arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kw)` |
| `get_names` | Yes | No | read-only candidate: typed adapter required | `(type='public_objects', enabled_only=0, selection='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_names_of_type` | Yes | No | read-only candidate: typed adapter required | `(type, public=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_object_list` | Yes | No | read-only candidate: typed adapter required | `(selection='(all)', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_type` | Yes | Yes | read-only candidate: typed adapter required | `(name, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `group` | Yes | Yes | manual review: NOT auto-authorized | `(name, members='', action='auto', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `join_states` | Yes | Yes | manual review: NOT auto-authorized | `(name, selection='all', mode=2, zoom=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `order` | Yes | Yes | manual review: NOT auto-authorized | `(names, sort=0, location='current', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `reinitialize` | Yes | Yes | blocked: never directly expose to LLM | `(what='everything', object='', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `remove` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(selection, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_name` | Yes | Yes | manual review: NOT auto-authorized | `(old_name, new_name, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `split_states` | Yes | Yes | manual review: NOT auto-authorized | `(object, first=1, last=0, prefix=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `ungroup` | Yes | Yes | manual review: NOT auto-authorized | `(members, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 03 Structure inspection

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `count_atoms` | Yes | Yes | read-only candidate: typed adapter required | `(selection='(all)', quiet=1, state=0, domain='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_angle` | Yes | Yes | read-only candidate: typed adapter required | `(atom1='pk1', atom2='pk2', atom3='pk3', state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_atom_coords` | Yes | No | read-only candidate: typed adapter required | `(selection, state=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_bonds` | Yes | No | read-only candidate: typed adapter required | `(selection='(all)', state=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_chains` | Yes | Yes | read-only candidate: typed adapter required | `(selection='(all)', state=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_coords` | Yes | No | read-only candidate: typed adapter required | `(selection='all', state=1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_coordset` | Yes | No | read-only candidate: typed adapter required | `(name, state=1, copy=1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_dihedral` | Yes | Yes | read-only candidate: typed adapter required | `(atom1='pk1', atom2='pk2', atom3='pk3', atom4='pk4', state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_distance` | Yes | Yes | read-only candidate: typed adapter required | `(atom1='pk1', atom2='pk2', state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_extent` | Yes | Yes | read-only candidate: typed adapter required | `(selection='(all)', state=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_model` | Yes | No | read-only candidate: typed adapter required | `(selection='(all)', state=1, ref='', ref_state=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_object_matrix` | Yes | No | read-only candidate: typed adapter required | `(object, state=1, incl_ttt=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_object_state` | Yes | No | read-only candidate: typed adapter required | `(name, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_position` | Yes | Yes | read-only candidate: typed adapter required | `(quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_selection_state` | Yes | No | read-only candidate: typed adapter required | `(selection, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_setting_float` | Yes | No | read-only candidate: typed adapter required | `(name, object='', state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_setting_int` | Yes | No | read-only candidate: typed adapter required | `(name, object='', state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_setting_text` | Yes | No | read-only candidate: typed adapter required | `(name, object='', state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_setting_tuple` | Yes | No | read-only candidate: typed adapter required | `(name, object='', state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_symmetry` | Yes | Yes | read-only candidate: typed adapter required | `(selection='(all)', state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_title` | Yes | Yes | read-only candidate: typed adapter required | `(object, state, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_version` | Yes | Yes | read-only candidate: typed adapter required | `(quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_view` | Yes | Yes | read-only candidate: typed adapter required | `(output=1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `identify` | Yes | Yes | read-only candidate: typed adapter required | `(selection='(all)', mode=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `index` | Yes | Yes | read-only candidate: typed adapter required | `(selection='(all)', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 04 Selection and atom queries

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `deprotect` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `deselect` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `flag` | Yes | Yes | manual review: NOT auto-authorized | `(flag, selection, action='reset', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_unused_name` | Yes | No | manual review: NOT auto-authorized | `(prefix='tmp', alwaysnumber=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `indicate` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(all)', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mask` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `pop` | Yes | Yes | manual review: NOT auto-authorized | `(name, source, enable=-1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `protect` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `select` | Yes | Yes | manual review: NOT auto-authorized | `(name, selection='', enable=-1, quiet=1, merge=0, state=0, domain='', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `unmask` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 05 Representation and color

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `cartoon` | Yes | Yes | manual review: NOT auto-authorized | `(type, selection='(all)', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `color` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(color, selection='(all)', quiet=1, flags=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `color_deep` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(color, name='all', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `dss` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(selection='(all)', state=0, context=None, preserve=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `hide` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(representation='everything', selection='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `label` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(selection='(all)', expression='', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `recolor` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(selection='all', representation='everything', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set` | Yes | Yes | manual review: NOT auto-authorized | `(name, value=1, selection='', state=0, updates=1, log=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_bond` | Yes | Yes | manual review: NOT auto-authorized | `(name, value, selection1, selection2=None, state=0, updates=1, log=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_color` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(name, rgb, mode=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_title` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(object, state, text, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `show` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(representation='wire', selection='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `show_as` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(representation='wire', selection='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `spectrum` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(expression='count', palette='rainbow', selection='(all)', minimum=None, maximum=None, byres=0, quiet=1, interpolation='rgb', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 06 Camera and viewport

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `center` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(selection='all', state=0, origin=1, animate=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `clip` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(mode, distance, selection=None, state=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `full_screen` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(toggle=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `matrix_copy` | Yes | Yes | manual review: NOT auto-authorized | `(source_name='', target_name='', source_mode=-1, target_mode=-1, source_state=1, target_state=1, target_undo=1, log=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `matrix_reset` | Yes | Yes | manual review: NOT auto-authorized | `(name, state=1, mode=-1, log=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `move` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(axis, distance, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `orient` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(selection='(all)', state=0, animate=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `origin` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(selection='(all)', object=None, position=None, state=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `reset` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(object='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `rock` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(mode=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `rotate` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(axis='x', angle=0.0, selection='all', state=-1, camera=1, object=None, origin=None, object_mode=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_view` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(view, animate=0, quiet=1, hand=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `translate` | Yes | Yes | manual review: NOT auto-authorized | `(vector=[0.0, 0.0, 0.0], selection='all', state=-1, camera=1, object=None, object_mode=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `turn` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(axis, angle, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `view` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(key, action='recall', animate=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `viewport` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(width=-1, height=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `zoom` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(selection='all', buffer=0.0, state=0, complete=0, animate=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 07 Distances and geometry

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `angle` | Yes | Yes | manual review: NOT auto-authorized | `(name=None, selection1='(pk1)', selection2='(pk2)', selection3='(pk3)', mode=None, label=1, reset=0, zoom=0, state=0, quiet=1, *, state1=-3, state2=-3, state3=-3, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `centerofmass` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(all)', state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `dihedral` | Yes | Yes | manual review: NOT auto-authorized | `(name=None, selection1='(pk1)', selection2='(pk2)', selection3='(pk3)', selection4='(pk4)', mode=None, label=1, reset=0, zoom=0, state=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `dist` | Yes | No | manual review: NOT auto-authorized | `(name=None, selection1='(pk1)', selection2='(pk2)', cutoff=None, mode=None, zoom=0, width=None, length=None, gap=None, label=1, quiet=1, reset=0, state=0, state1=-3, state2=-3, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `distance` | Yes | Yes | manual review: NOT auto-authorized | `(name=None, selection1='(pk1)', selection2='(pk2)', cutoff=None, mode=None, zoom=0, width=None, length=None, gap=None, label=1, quiet=1, reset=0, state=0, state1=-3, state2=-3, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_dihedral` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(atom1, atom2, atom3, atom4, angle, state=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 08 Structure alignment

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `align` | Yes | Yes | manual review: NOT auto-authorized | `(mobile, target, cutoff=2.0, cycles=5, gap=-10.0, extend=-0.5, max_gap=50, object=None, matrix='BLOSUM62', mobile_state=0, target_state=0, quiet=1, max_skip=0, transform=1, reset=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `cealign` | Yes | Yes | manual review: NOT auto-authorized | `(target, mobile, target_state=1, mobile_state=1, quiet=1, guide=1, d0=3.0, d1=4.0, window=8, gap_max=30, transform=1, object=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `fit` | Yes | Yes | manual review: NOT auto-authorized | `(mobile, target, mobile_state=0, target_state=0, quiet=1, matchmaker=0, cutoff=2.0, cycles=0, object=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_raw_alignment` | Yes | No | read-only candidate: typed adapter required | `(name='', active_only=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `intra_fit` | Yes | Yes | manual review: NOT auto-authorized | `(selection, state=1, quiet=1, mix=0, *, pbc=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `intra_rms` | Yes | Yes | manual review: NOT auto-authorized | `(selection, state=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `intra_rms_cur` | Yes | Yes | manual review: NOT auto-authorized | `(selection, state=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `pair_fit` | Yes | Yes | manual review: NOT auto-authorized | `(*arg, quiet=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `rms` | Yes | Yes | manual review: NOT auto-authorized | `(mobile, target, mobile_state=0, target_state=0, quiet=1, matchmaker=0, cutoff=2.0, cycles=0, object=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `rms_cur` | Yes | Yes | manual review: NOT auto-authorized | `(mobile, target, mobile_state=0, target_state=0, quiet=1, matchmaker=0, cutoff=2.0, cycles=0, object=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `super` | Yes | Yes | manual review: NOT auto-authorized | `(mobile, target, cutoff=2.0, cycles=5, gap=-1.5, extend=-0.7, max_gap=50, object=None, matrix='BLOSUM62', mobile_state=0, target_state=0, quiet=1, max_skip=0, transform=1, reset=0, seq=0.0, radius=12.0, scale=17.0, base=0.65, coord=0.0, expect=6.0, window=3, ante=-1.0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 09 Surface and accessibility

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `get_area` | Yes | Yes | read-only candidate: typed adapter required | `(selection='(all)', state=1, load_b=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_sasa_relative` | Yes | Yes | read-only candidate: typed adapter required | `(selection='all', state=1, vis=-1, var='b', quiet=1, outfile='', *, subsele='all', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `isodot` | Yes | Yes | manual review: NOT auto-authorized | `(name, map, level=1.0, selection='', buffer=0.0, state=0, carve=None, source_state=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `isomesh` | Yes | Yes | manual review: NOT auto-authorized | `(name, map, level=1.0, selection='', buffer=0.0, state=1, carve=None, source_state=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `isosurface` | Yes | Yes | manual review: NOT auto-authorized | `(name, map, level=1.0, selection='', buffer=0.0, state=1, carve=None, source_state=0, side=1, mode=3, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 10 Editing and mutations

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `alter` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(selection, expression, quiet=1, space=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `alter_state` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(state, selection, expression, quiet=1, space=None, atomic=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `attach` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(element, geometry, valence, name='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `bond` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(atom1='pk1', atom2='pk2', order=1, *, quiet=1, symop='', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `edit` | Yes | Yes | manual review: NOT auto-authorized | `(selection1='', selection2='none', selection3='none', selection4='none', pkresi=0, pkbond=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `fab` | Yes | Yes | manual review: NOT auto-authorized | `(input, name=None, mode='peptide', resi=1, chain='', segi='', state=-1, dir=1, hydro=-1, ss=0, async_=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `fragment` | Yes | Yes | manual review: NOT auto-authorized | `(name, object=None, origin=1, zoom=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `fuse` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(selection1='(pk1)', selection2='(pk2)', mode=0, recolor=1, move=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `h_add` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(selection='(all)', quiet=1, state=0, legacy=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `h_fill` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `iterate` | Yes | Yes | manual review: NOT auto-authorized | `(selection, expression, quiet=1, space=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `iterate_state` | Yes | Yes | manual review: NOT auto-authorized | `(state, selection, expression, quiet=1, space=None, atomic=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `pseudoatom` | Yes | Yes | manual review: NOT auto-authorized | `(object='', selection='', name='PS1', resn='PSD', resi='1', chain='P', segi='PSDO', elem='PS', vdw=-1.0, hetatm=1, b=0.0, q=0.0, color='', label='', pos=None, state=0, mode='rms', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `push_undo` | Yes | No | manual review: NOT auto-authorized | `(selection, just_coordinates=1, finish_undo=0, add_objects=0, delete_objects=0, state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `redo` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `replace` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(element, geometry, valence, h_fill=1, name='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `sculpt_activate` | Yes | Yes | manual review: NOT auto-authorized | `(object, state=0, match_state=-1, match_by_segment=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `sculpt_deactivate` | Yes | Yes | manual review: NOT auto-authorized | `(object, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `sculpt_iterate` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(object, state=-1, cycles=10, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `smooth` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(selection='all', passes=1, window=5, first=1, last=0, ends=0, quiet=1, *, cutoff=-1, pbc=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `sort` | Yes | Yes | manual review: NOT auto-authorized | `(object='', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `unbond` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(atom1='(pk1)', atom2='(pk2)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `undo` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 11 Maps and volumetric

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `gradient` | Yes | Yes | manual review: NOT auto-authorized | `(name, map, minimum=1.0, maximum=-1.0, selection='', buffer=0.0, state=0, carve=None, source_state=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `isolevel` | Yes | Yes | manual review: NOT auto-authorized | `(name, level=1.0, state=0, query=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `map_double` | Yes | Yes | manual review: NOT auto-authorized | `(name, state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `map_new` | Yes | Yes | manual review: NOT auto-authorized | `(name, type='gaussian', grid=None, selection='(all)', buffer=None, box=None, state=0, quiet=1, zoom=0, normalize=-1, clamp=[1.0, -1.0], resolution=0.0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `map_set` | Yes | Yes | manual review: NOT auto-authorized | `(name, operator, operands='', target_state=0, source_state=0, zoom=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `map_set_border` | Yes | Yes | manual review: NOT auto-authorized | `(name, level=0.0, state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `map_trim` | Yes | Yes | manual review: NOT auto-authorized | `(name, selection, buffer=0.0, map_state=0, sele_state=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `ramp_new` | Yes | Yes | manual review: NOT auto-authorized | `(name, map_name, range=[-1.0, 0.0, 1.0], color=['red', [1.0, 1.0, 1.0], 'blue'], state=1, selection='', beyond=2.0, within=6.0, sigma=2.0, zero=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `slice_new` | Yes | Yes | manual review: NOT auto-authorized | `(name, map, state=1, source_state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `volume` | Yes | Yes | manual review: NOT auto-authorized | `(name, map, ramp='', selection='', buffer=0.0, state=1, carve=None, source_state=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `volume_color` | Yes | Yes | manual review: NOT auto-authorized | `(name, ramp='', state=-1, quiet=1, _guiupdate=True, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `volume_ramp_new` | Yes | Yes | manual review: NOT auto-authorized | `(name, ramp)` |

### 12 States and trajectories

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `count_frames` | Yes | Yes | read-only candidate: typed adapter required | `(quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `frame` | Yes | Yes | manual review: NOT auto-authorized | `(frame, trigger=-1, scene=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `morph` | Yes | Yes | manual review: NOT auto-authorized | `(name, sele1, sele2=None, state1=-1, state2=-1, refinement=3, steps=30, method='rigimol', match='align', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 13 Movies and scenes

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `backward` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `ending` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `forward` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mclear` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mdo` | Yes | Yes | manual review: NOT auto-authorized | `(frame, command, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `middle` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mplay` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mset` | Yes | Yes | manual review: NOT auto-authorized | `(specification='', frame=1, freeze=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mstop` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mview` | Yes | Yes | manual review: NOT auto-authorized | `(action='store', first=0, last=0, power=0.0, bias=-1.0, simple=-1, linear=0.0, object='', wrap=-1, hand=0, window=5, cycles=1, scene='', cut=0.5, quiet=1, auto=-1, state=0, freeze=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `rewind` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `scene` | Yes | Yes | manual review: NOT auto-authorized | `(key='auto', action='recall', message=None, view=1, color=1, active=1, rep=1, frame=1, animate=-1, new_key=None, hand=1, quiet=1, sele='all', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 14 Rendering and figures

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `bg_color` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(color='black', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `capture` | Yes | Yes | manual review: NOT auto-authorized | `(quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `draw` | Yes | Yes | manual review: NOT auto-authorized | `(width=0, height=0, antialias=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get` | Yes | Yes | manual review: NOT auto-authorized | `(name, selection='', state=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `ray` | Yes | Yes | manual review: NOT auto-authorized | `(width=0, height=0, antialias=-1, angle=0.0, shift=0.0, renderer=-1, quiet=1, async_=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `stereo` | Yes | Yes | manual review: NOT auto-authorized | `(toggle='on', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 15 Settings and configuration

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `button` | Yes | Yes | manual review: NOT auto-authorized | `(button, modifier, action, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `config_mouse` | Yes | Yes | manual review: NOT auto-authorized | `(ring='three_button', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mouse` | Yes | Yes | manual review: NOT auto-authorized | `(action=None, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `unset` | Yes | Yes | manual review: NOT auto-authorized | `(name, selection='', state=0, updates=1, log=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `unset_deep` | Yes | Yes | manual review: NOT auto-authorized | `(settings='', object='*', updates=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 16 Crystallography and symmetry

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `set_symmetry` | Yes | Yes | manual review: NOT auto-authorized | `(selection, a, b, c, alpha, beta, gamma, spacegroup='P1', state=-1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `symexp` | Yes | Yes | manual review: NOT auto-authorized | `(prefix, object, selection, cutoff, segi=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |

### 17 Command language and extension

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `alias` | Yes | Yes | blocked: never directly expose to LLM | `(name, command, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `cd` | Yes | Yes | blocked: never directly expose to LLM | `(dir='~', complain=1, quiet=1)` |
| `commands` | Yes | No | manual review: NOT auto-authorized | `()` |
| `do` | Yes | No | blocked: never directly expose to LLM | `(commands, log=1, echo=1, flush=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `extend` | Yes | No | blocked: never directly expose to LLM | `(name, function=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `extendaa` | Yes | No | blocked: never directly expose to LLM | `(*arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `help` | Yes | Yes | manual review: NOT auto-authorized | `(command='commands', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `log_close` | Yes | Yes | blocked: never directly expose to LLM | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `log_open` | Yes | Yes | blocked: never directly expose to LLM | `(filename='log.pml', mode='w', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `ls` | Yes | Yes | manual review: NOT auto-authorized | `(pattern=None)` |
| `pwd` | Yes | Yes | manual review: NOT auto-authorized | `()` |
| `python` | No | Yes | blocked: never directly expose to LLM | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `quit` | Yes | Yes | blocked: never directly expose to LLM | `(code=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `run` | Yes | Yes | blocked: never directly expose to LLM | `(filename, namespace='global', _spawn=0, _self=None)` |
| `system` | Yes | Yes | blocked: never directly expose to LLM | `(command, async_=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |

### 99 Uncategorized / review

| Name | API | PML | Risk | Signature |
|---|:---:|:---:|---|---|
| `abort` | Yes | Yes | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `accept` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `add_bond` | Yes | No | manual review: NOT auto-authorized | `(oname, index1, index2, order=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `alignto` | Yes | Yes | manual review: NOT auto-authorized | `(target='', method='cealign', selection='', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `alphatoall` | Yes | Yes | manual review: NOT auto-authorized | `(selection='polymer', properties='b', operator='byca', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `alter_list` | Yes | No | manual review: NOT auto-authorized | `(object, expr_list, quiet=1, space=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `api` | Yes | Yes | manual review: NOT auto-authorized | `(name, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `as` | No | Yes | manual review: NOT auto-authorized | `(representation='wire', selection='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `as_pathstr` | Yes | No | manual review: NOT auto-authorized | `(path)` |
| `assert` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `assign_stereo` | Yes | Yes | manual review: NOT auto-authorized | `(selection='all', state=-1, method='', quiet=1, prop='stereo', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `async_` | Yes | No | manual review: NOT auto-authorized | `(func, *args, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `auto_measure` | Yes | No | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `bg_colour` | Yes | Yes | manual review: NOT auto-authorized | `(color='black', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `block_flush` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `boolean_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `cache` | Yes | Yes | manual review: NOT auto-authorized | `(action='optimize', scenes='', state=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `callout` | Yes | Yes | manual review: NOT auto-authorized | `(name, label, pos='', screen='auto', state=-1, color='front', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `check` | Yes | Yes | manual review: NOT auto-authorized | `(selection=None, preserve=0)` |
| `class` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `clean` | Yes | Yes | manual review: NOT auto-authorized | `(selection, present='', state=-1, fix='', restrain='', method='mmff', async_=0, save_undo=1, message=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `cls` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `colour` | Yes | Yes | manual review: NOT auto-authorized | `(color, selection='(all)', quiet=1, flags=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `contour_sc` | Yes | No | manual review: NOT auto-authorized | `(sc=<class 'pymol.shortcut.Shortcut'>, gnot=<function get_names_of_type at 0x10b4031c0>)` |
| `copy_image` | Yes | No | manual review: NOT auto-authorized | `(quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `copy_to` | Yes | Yes | manual review: NOT auto-authorized | `(name, selection, rename='chain segi ID', zoom=-1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `count_discrete` | Yes | Yes | manual review: NOT auto-authorized | `(selection, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `curve_new` | Yes | Yes | manual review: NOT auto-authorized | `(name='', curve_type='bezier', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `cycle_valence` | Yes | Yes | manual review: NOT auto-authorized | `(h_fill=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `declare_command` | Yes | No | manual review: NOT auto-authorized | `(name, function=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `decline` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `def` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `del` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `del_colorection` | Yes | No | manual review: NOT auto-authorized | `(dict, key, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `delete_states` | Yes | Yes | manual review: NOT auto-authorized | `(name: str, states: str, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `desaturate` | Yes | Yes | manual review: NOT auto-authorized | `(selection='all', a=0.5, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `diagnostics` | No | Yes | manual review: NOT auto-authorized | `(filename='', compact=0, quiet=1)` |
| `dir` | No | Yes | manual review: NOT auto-authorized | `(pattern=None)` |
| `dirty` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `dirty_wizard` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `download_chem_comp` | Yes | No | manual review: NOT auto-authorized | `(resn, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `drag` | Yes | Yes | manual review: NOT auto-authorized | `(selection=None, wizard=1, edit=1, quiet=1, mode=-1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `dump` | Yes | Yes | manual review: NOT auto-authorized | `(fnam, obj, state=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `edit_mode` | Yes | Yes | manual review: NOT auto-authorized | `(active=1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `editing_ring` | Yes | Yes | manual review: NOT auto-authorized | `(action, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `embed` | No | Yes | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `exec` | No | Yes | blocked: never directly expose to LLM | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `exp_path` | Yes | No | manual review: NOT auto-authorized | `(path)` |
| `extra_fit` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(all)', reference='', method='align', zoom=1, quiet=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `fast_minimize` | Yes | No | manual review: NOT auto-authorized | `(*args, **kwargs)` |
| `fb_action` | Yes | No | manual review: NOT auto-authorized | `()` |
| `fb_action_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `fb_mask` | Yes | No | manual review: NOT auto-authorized | `()` |
| `fb_mask_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `fb_module` | Yes | No | manual review: NOT auto-authorized | `()` |
| `fb_module_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `feedback` | Yes | Yes | manual review: NOT auto-authorized | `(action='?', module='?', mask='?', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `file_read` | Yes | No | manual review: NOT auto-authorized | `(finfo, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `filename_to_objectname` | Yes | No | manual review: NOT auto-authorized | `(fname, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `find_pairs` | Yes | No | manual review: NOT auto-authorized | `(selection1, selection2, state1=1, state2=1, cutoff=3.5, mode=0, angle=45, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `finish_object` | Yes | No | manual review: NOT auto-authorized | `(name, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `fix_chemistry` | Yes | Yes | manual review: NOT auto-authorized | `(selection1='all', selection2='all', invalidate=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `fnab` | Yes | Yes | manual review: NOT auto-authorized | `(input, name=None, mode='DNA', form='B', dbl_helix=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `focal_blur` | Yes | Yes | manual review: NOT auto-authorized | `(aperture=2.0, samples=10, ray=0, filename='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `for` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `fork` | No | Yes | blocked: never directly expose to LLM | `(filename, namespace='module', _self=None)` |
| `get_assembly_ids` | Yes | No | manual review: NOT auto-authorized | `(name, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_bond` | Yes | Yes | manual review: NOT auto-authorized | `(name, selection1, selection2=None, state=0, updates=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_bond_print` | Yes | No | manual review: NOT auto-authorized | `(obj, max_bond, max_type, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_bytes` | Yes | No | manual review: NOT auto-authorized | `(format, selection='(all)', state=-1, ref='', ref_state=-1, multi=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_clip` | Yes | Yes | manual review: NOT auto-authorized | `(quiet: int = 1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_collada` | Yes | No | manual review: NOT auto-authorized | `(version=2, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_color_index` | Yes | No | manual review: NOT auto-authorized | `(color, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_color_indices` | Yes | No | manual review: NOT auto-authorized | `(all=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_color_tuple` | Yes | No | manual review: NOT auto-authorized | `(name, mode=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_colorection` | Yes | No | manual review: NOT auto-authorized | `(key, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_drag_object_name` | Yes | No | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_editor_scheme` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_fastastr` | Yes | No | manual review: NOT auto-authorized | `(selection='all', state=-1, quiet=1, key='', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_frame` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_gltf` | Yes | No | manual review: NOT auto-authorized | `(filename, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_idtf` | Yes | No | manual review: NOT auto-authorized | `(quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_legal_name` | Yes | No | manual review: NOT auto-authorized | `(name, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_modal_draw` | Yes | No | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, quiet=1)` |
| `get_movie_length` | Yes | No | manual review: NOT auto-authorized | `(quiet=1, images=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_movie_locked` | Yes | No | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_movie_playing` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_mtl_obj` | Yes | No | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_object_color_index` | Yes | No | manual review: NOT auto-authorized | `(name, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_object_settings` | Yes | No | manual review: NOT auto-authorized | `(object, state=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_object_ttt` | Yes | No | manual review: NOT auto-authorized | `(object, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_phipsi` | Yes | No | manual review: NOT auto-authorized | `(selection='(name CA)', state=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_povray` | Yes | No | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_progress` | Yes | No | manual review: NOT auto-authorized | `(reset=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_renderer` | Yes | Yes | manual review: NOT auto-authorized | `(quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_scene_list` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_scene_message` | Yes | No | manual review: NOT auto-authorized | `(name, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_scene_thumbnail` | Yes | No | manual review: NOT auto-authorized | `(name, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_setting_boolean` | Yes | No | manual review: NOT auto-authorized | `(name, object='', state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_setting_legacy` | Yes | No | manual review: NOT auto-authorized | `(name, object='', state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_setting_updates` | Yes | No | manual review: NOT auto-authorized | `(object='', state=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_state` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_str` | Yes | No | manual review: NOT auto-authorized | `(format, selection='(all)', state=-1, ref='', ref_state=-1, multi=-1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_viewport` | Yes | Yes | manual review: NOT auto-authorized | `(output=1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_vis` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_volume_field` | Yes | No | manual review: NOT auto-authorized | `(objName, state=1, copy=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_volume_histogram` | Yes | No | manual review: NOT auto-authorized | `(objName, bins=64, range=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_vrml` | Yes | No | manual review: NOT auto-authorized | `(version=2, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_wizard` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `get_wizard_stack` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `global` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `group_sc` | Yes | No | manual review: NOT auto-authorized | `(sc=<class 'pymol.shortcut.Shortcut'>, gnot=<function get_names_of_type at 0x10b4031c0>)` |
| `h_fix` | Yes | Yes | manual review: NOT auto-authorized | `(selection='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `help_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `help_setting` | Yes | Yes | manual review: NOT auto-authorized | `(name, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `id_atom` | Yes | Yes | manual review: NOT auto-authorized | `(selection, mode=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `if` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `import` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `interrupt` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `invert` | Yes | Yes | manual review: NOT auto-authorized | `(quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `ipython_image` | Yes | No | manual review: NOT auto-authorized | `(*args, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `is_dict` | Yes | No | manual review: NOT auto-authorized | `(obj)` |
| `is_error` | Yes | No | manual review: NOT auto-authorized | `(result)` |
| `is_gui_thread` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `is_list` | Yes | No | manual review: NOT auto-authorized | `(obj)` |
| `is_ok` | Yes | No | manual review: NOT auto-authorized | `(result)` |
| `is_sequence` | Yes | No | manual review: NOT auto-authorized | `(obj)` |
| `is_string` | Yes | No | manual review: NOT auto-authorized | `(obj)` |
| `is_tuple` | Yes | No | manual review: NOT auto-authorized | `(obj)` |
| `kwhash` | Yes | No | manual review: NOT auto-authorized | `()` |
| `label2` | Yes | No | manual review: NOT auto-authorized | `(selection='(all)', expression='', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_brick` | Yes | No | manual review: NOT auto-authorized | `(*arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kw)` |
| `load_callback` | Yes | No | manual review: NOT auto-authorized | `(*arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_coords` | Yes | No | manual review: NOT auto-authorized | `(coords, selection, state=1, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_coordset` | Yes | No | manual review: NOT auto-authorized | `(coords, object, state=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_embedded` | Yes | Yes | manual review: NOT auto-authorized | `(key=None, name=None, state=0, finish=1, discrete=1, quiet=1, zoom=-1, multiplex=-2, object_props=None, atom_props=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_map` | Yes | No | manual review: NOT auto-authorized | `(*arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kw)` |
| `load_mtz` | Yes | Yes | manual review: NOT auto-authorized | `(filename, prefix='', amplitudes='', phases='', weights='None', reso_low=0, reso_high=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_object` | Yes | No | manual review: NOT auto-authorized | `(type, object, name, state=0, finish=1, discrete=0, quiet=1, zoom=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_png` | Yes | Yes | manual review: NOT auto-authorized | `(filename, movie=1, stereo=-1, quiet=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `load_raw` | Yes | No | manual review: NOT auto-authorized | `(content, format, object='', state=0, finish=1, discrete=-1, quiet=1, multiplex=None, zoom=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `loadable` | Yes | No | manual review: NOT auto-authorized | `()` |
| `loadall` | Yes | Yes | manual review: NOT auto-authorized | `(pattern, group='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwargs)` |
| `location_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `lock` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `lock_attempt` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `lock_without_glut` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `LockCM` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `log` | Yes | Yes | manual review: NOT auto-authorized | `(text, alt_text=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `look_at` | Yes | Yes | manual review: NOT auto-authorized | `(target_obj: str, mobile_obj: str = '_Camera', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `madd` | Yes | Yes | manual review: NOT auto-authorized | `(specification='', frame=0, freeze=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `map_generate` | Yes | No | manual review: NOT auto-authorized | `(name, reflection_file, amplitudes, phases, weights='None', reso_low=50.0, reso_high=1.0, quiet=1, zoom=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `map_halve` | Yes | Yes | manual review: NOT auto-authorized | `(name, state=0, smooth=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `map_sc` | Yes | No | manual review: NOT auto-authorized | `(sc=<class 'pymol.shortcut.Shortcut'>, gnot=<function get_names_of_type at 0x10b4031c0>)` |
| `mappend` | Yes | Yes | manual review: NOT auto-authorized | `(frame, command, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `matrix_transfer` | Yes | Yes | manual review: NOT auto-authorized | `(source_name='', target_name='', source_mode=-1, target_mode=-1, source_state=1, target_state=1, target_undo=1, log=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mcopy` | Yes | Yes | manual review: NOT auto-authorized | `(target, source=0, count=-1, freeze=0, object='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mdelete` | Yes | Yes | manual review: NOT auto-authorized | `(count=-1, frame=0, freeze=0, object='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mdump` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mem` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `meter_reset` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `minimize` | Yes | No | manual review: NOT auto-authorized | `(sele='', iter=500, grad=0.01, interval=50, _setup=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `minsert` | Yes | Yes | manual review: NOT auto-authorized | `(count, frame=0, freeze=0, object='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mmatrix` | Yes | Yes | manual review: NOT auto-authorized | `(action, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mmove` | Yes | Yes | manual review: NOT auto-authorized | `(target, source=0, count=-1, freeze=0, object='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `move_on_curve` | Yes | No | manual review: NOT auto-authorized | `(mobile_obj: str, curve_obj: str, t: float, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>) -> None` |
| `movie.load` | No | Yes | manual review: NOT auto-authorized | `(pattern, nam='mov', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kw)` |
| `movie.nutate` | No | Yes | manual review: NOT auto-authorized | `(first, last, angle=30, phase=0, loop=1, shift=1.5707963267948966, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `movie.pause` | No | Yes | manual review: NOT auto-authorized | `(pause=15, cycles=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `movie.produce` | No | Yes | manual review: NOT auto-authorized | `(filename, mode='', first=0, last=0, preserve=0, encoder='', quality=-1, quiet=1, width=0, height=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `movie.rock` | No | Yes | manual review: NOT auto-authorized | `(first=1, last=-1, angle=30, phase=0, loop=1, axis='y', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `movie.roll` | No | Yes | manual review: NOT auto-authorized | `(first=1, last=-1, loop=1, axis='y', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `movie.screw` | No | Yes | manual review: NOT auto-authorized | `(first, last, step=1, angle=30, phase=0, loop=1, axis='y', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `movie.sweep` | No | Yes | manual review: NOT auto-authorized | `(pause=0, cycles=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `movie.tdroll` | No | Yes | manual review: NOT auto-authorized | `(first, rangex, rangey, rangez, skip=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `movie.zoom` | No | Yes | manual review: NOT auto-authorized | `(first, last, step=1, loop=1, axis='z', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mse2met` | Yes | Yes | manual review: NOT auto-authorized | `(selection='all', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `mtoggle` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `multifilenamegen` | Yes | No | manual review: NOT auto-authorized | `(filename, selection, state, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `object_sc` | Yes | No | manual review: NOT auto-authorized | `(sc=<class 'pymol.shortcut.Shortcut'>, gn=<function get_names at 0x10b402a30>)` |
| `overlap` | Yes | Yes | manual review: NOT auto-authorized | `(selection1, selection2, state1=1, state2=1, adjust=0.0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `palette_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `pass` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `paste` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `pbc_unwrap` | Yes | Yes | manual review: NOT auto-authorized | `(oname, bymol=True, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `pbc_wrap` | Yes | Yes | manual review: NOT auto-authorized | `(oname, center=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `phi_psi` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(byres pk1)', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `pi_interactions` | Yes | Yes | manual review: NOT auto-authorized | `(name='', selection1='all', selection2='same', state=0, state1=-3, state2=-3, quiet=1, reset=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `pretty` | Yes | No | manual review: NOT auto-authorized | `(selection='(all)', *, solv=False, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `print` | No | Yes | manual review: NOT auto-authorized | `(*args, **_)` |
| `publication` | Yes | No | manual review: NOT auto-authorized | `(selection='(all)', *, solv=False, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `python_help` | Yes | No | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `QuietException` | Yes | No | manual review: NOT auto-authorized | `<unavailable>` |
| `raise` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `ramp_update` | Yes | Yes | manual review: NOT auto-authorized | `(name, range=[], color=[], quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `read_mmodstr` | Yes | No | manual review: NOT auto-authorized | `(content, name, state=0, quiet=1, zoom=-1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kw)` |
| `read_sdfstr` | Yes | No | manual review: NOT auto-authorized | `(sdfstr, name, state=0, finish=1, discrete=1, quiet=1, zoom=-1, multiplex=-2, object_props=None, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `read_xplorstr` | Yes | No | manual review: NOT auto-authorized | `(xplor, name, state=0, finish=1, discrete=0, quiet=1, zoom=-1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `ready` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `rebond` | Yes | Yes | manual review: NOT auto-authorized | `(oname, state=-1, *, pbc=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `rebuild` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(selection='all', representation='everything', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `recolour` | Yes | Yes | manual review: NOT auto-authorized | `(selection='all', representation='everything', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `reference` | Yes | Yes | manual review: NOT auto-authorized | `(action='validate', selection='(all)', state=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `refresh` | Yes | Yes | view candidate: bounded parameters and undo strategy | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `refresh_wizard` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `remove_picked` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(hydrogens=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `rename` | Yes | Yes | mutation: approval or dedicated guarded workflow | `(selection='all', force=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `replace_wizard` | Yes | Yes | manual review: NOT auto-authorized | `(name=None, *arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwd)` |
| `repmasks_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `repres_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `resume` | Yes | Yes | manual review: NOT auto-authorized | `(filename, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `safe_alpha_list_eval` | Yes | No | manual review: NOT auto-authorized | `(st)` |
| `safe_eval` | Yes | No | manual review: NOT auto-authorized | `(st)` |
| `safe_list_eval` | Yes | No | manual review: NOT auto-authorized | `(st)` |
| `SafeEvalNS` | Yes | No | manual review: NOT auto-authorized | `()` |
| `scene_order` | Yes | Yes | manual review: NOT auto-authorized | `(names, sort=0, location='current', quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `scene_recall_message` | Yes | No | manual review: NOT auto-authorized | `(message, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `sculpt_purge` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `select_list` | Yes | No | manual review: NOT auto-authorized | `(name, object, id_list, state=0, mode='id', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `selection_sc` | Yes | No | manual review: NOT auto-authorized | `(sc=<class 'pymol.shortcut.Shortcut'>, gn=<function get_names at 0x10b402a30>)` |
| `set_colorection` | Yes | No | manual review: NOT auto-authorized | `(dict, key, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_colour` | Yes | Yes | manual review: NOT auto-authorized | `(name, rgb, mode=0, quiet=1, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_discrete` | Yes | No | manual review: NOT auto-authorized | `(name, discrete=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_frame` | Yes | No | manual review: NOT auto-authorized | `(frame=1, mode=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_geometry` | Yes | Yes | manual review: NOT auto-authorized | `(selection, geometry, valence, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_key` | Yes | Yes | manual review: NOT auto-authorized | `(key, fn=None, arg=(), kw={}, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_object_color` | Yes | No | manual review: NOT auto-authorized | `(name, color, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_object_ttt` | Yes | No | manual review: NOT auto-authorized | `(object, ttt, state=0, quiet=1, homogenous=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_raw_alignment` | Yes | No | manual review: NOT auto-authorized | `(name, raw, guide='', state=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_scene_message` | Yes | No | manual review: NOT auto-authorized | `(name, message, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_state_order` | Yes | No | manual review: NOT auto-authorized | `(name, order, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_vis` | Yes | No | manual review: NOT auto-authorized | `(dict, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_wizard` | Yes | No | manual review: NOT auto-authorized | `(wizard=None, replace=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `set_wizard_stack` | Yes | No | manual review: NOT auto-authorized | `(stack=[], _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `Shortcut` | Yes | No | manual review: NOT auto-authorized | `(keywords=(), filter_leading_underscore=1)` |
| `show_help` | Yes | No | manual review: NOT auto-authorized | `(cmmd, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `simple` | Yes | No | manual review: NOT auto-authorized | `(selection='(all)', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `skip` | No | Yes | manual review: NOT auto-authorized | `(*, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `space` | Yes | Yes | manual review: NOT auto-authorized | `(space='', gamma=1.0, quiet=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `space_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `spawn` | Yes | Yes | blocked: never directly expose to LLM | `(filename, namespace='module', _self=None)` |
| `spheroid` | Yes | Yes | manual review: NOT auto-authorized | `(object='', average=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `splash` | Yes | Yes | manual review: NOT auto-authorized | `(mode=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `split_chains` | Yes | Yes | manual review: NOT auto-authorized | `(selection='(all)', prefix=None, group=None, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `stereo_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `symmetry_copy` | Yes | Yes | manual review: NOT auto-authorized | `(source_name, target_name, source_state=1, target_state=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `sync` | Yes | No | manual review: NOT auto-authorized | `(timeout=1.0, poll=0.05, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `technical` | Yes | No | manual review: NOT auto-authorized | `(selection='(all)', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `test` | Yes | No | manual review: NOT auto-authorized | `(group=0, index=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `toggle` | Yes | Yes | manual review: NOT auto-authorized | `(representation='lines', selection='all', *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `toggle_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `torsion` | Yes | Yes | manual review: NOT auto-authorized | `(angle, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `transform_object` | Yes | No | manual review: NOT auto-authorized | `(name, matrix, state=-1, log=0, selection='', homogenous=0, transpose=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `transform_selection` | Yes | No | manual review: NOT auto-authorized | `(selection, matrix, state=-1, log=0, homogenous=0, transpose=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `translate_atom` | Yes | No | manual review: NOT auto-authorized | `(sele1, v0, v1, v2, state=0, mode=0, log=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `try` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `unblock_flush` | Yes | No | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `uniquify` | Yes | Yes | manual review: NOT auto-authorized | `(identifier, selection, reference='', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `unlock` | Yes | No | manual review: NOT auto-authorized | `(result=None, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `unpick` | Yes | Yes | manual review: NOT auto-authorized | `(_self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `unset_bond` | Yes | Yes | manual review: NOT auto-authorized | `(name, selection1, selection2=None, state=0, updates=1, log=0, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `update` | Yes | Yes | manual review: NOT auto-authorized | `(target, source, target_state=0, source_state=0, matchmaker=1, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbab` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbac` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbag` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbak` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbam` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbao` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbap` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbas` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbaw` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbay` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cbc` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', first_color=7, quiet=1, legacy=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.chainbow` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', palette='rainbow', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.cnc` | No | Yes | manual review: NOT auto-authorized | `(selection='(all)', quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.mrock` | No | Yes | manual review: NOT auto-authorized | `(first=1, last=-1, angle=30, phase=0, loop=1, axis='y', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.mroll` | No | Yes | manual review: NOT auto-authorized | `(first=1, last=-1, loop=1, axis='y', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.rainbow` | No | Yes | manual review: NOT auto-authorized | `(selection="(name CA and alt ''+A)", reverse=0, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `util.ss` | No | Yes | manual review: NOT auto-authorized | `(selection="(name CA and alt '',A)", state=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `valence` | Yes | Yes | manual review: NOT auto-authorized | `(order, selection1=None, selection2=None, source='', target_state=0, source_state=0, reset=1, quiet=1, *, symop='', _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `vdw_fit` | Yes | Yes | manual review: NOT auto-authorized | `(selection1, selection2, state1=1, state2=1, buffer=0.24, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `volume_panel` | Yes | Yes | manual review: NOT auto-authorized | `(name, quiet=1, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, _noqt=0)` |
| `while` | No | Yes | manual review: NOT auto-authorized | `(string, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `window` | Yes | Yes | manual review: NOT auto-authorized | `(action='show', x=0, y=0, width=0, height=0, *, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>)` |
| `window_sc` | Yes | No | manual review: NOT auto-authorized | `()` |
| `wizard` | Yes | Yes | manual review: NOT auto-authorized | `(name=None, *arg, _self=<module 'pymol.cmd' from '/opt/homebrew/Cellar/pymol/3.1.0_3/libexec/lib/python3.14/site-packages/pymol/cmd.py'>, **kwd)` |
| `write_html_ref` | Yes | No | manual review: NOT auto-authorized | `(file)` |
