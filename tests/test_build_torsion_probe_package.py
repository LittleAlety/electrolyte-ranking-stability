"""Torsion packaging must change an internal coordinate, not rotate the molecule."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts/wp_production"))
spec = importlib.util.spec_from_file_location("torsion_package", REPO / "scripts/wp_production/build_torsion_probe_package.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_each_batch_reads_its_own_list():
    template = '#SBATCH --array=0-%d\ntask=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" tasks.txt)\n'
    assert 'p" batch_2.txt)' in m.render_batch_script(template, 2, 3)
    assert '#SBATCH --array=0-2' in m.render_batch_script(template, 2, 3)
    assert 'p" tasks.txt)' not in m.render_batch_script(template, 1, 8)


@pytest.mark.parametrize("tasks,chunks", [
    (["a", "b"], [["a"], ["a"]]),
    (["a", "b"], [["a"]]),
    (["a", "a"], [["a"], ["a"]]),
])
def test_batch_overlap_or_missing_fails(tasks, chunks):
    with pytest.raises(ValueError):
        m.validate_batch_partition(tasks, chunks)


def test_fragment_rotation_keeps_opposite_side_fixed():
    xyz = np.array([[0, 1, 0], [0, 0, 0], [1, 0, 0], [1, 1, 0]], dtype=float)
    adj = [{1}, {0, 2}, {1, 3}, {2}]
    result, audit = m.rotate_fragment(xyz, (0, 1, 2, 3), adj,
                                    single_bonds={(0, 1), (1, 2), (2, 3)}, degrees=60)
    assert np.allclose(result[2:], xyz[2:])
    assert not np.allclose(result[0], xyz[0])
    assert audit["pair_distance_change_a"] > 0.1
    assert audit["moving_indices"] == [0, 1]


def test_ring_and_multiple_bond_are_not_rotatable():
    xyz = np.array([[0, 1, 0], [0, 0, 0], [1, 0, 0], [1, 1, 0]], dtype=float)
    with pytest.raises(ValueError, match="single"):
        m.rotate_fragment(xyz, (0, 1, 2, 3), [{1}, {0, 2}, {1, 3}, {2}],
                          single_bonds={(0, 1), (2, 3)}, degrees=60)
    with pytest.raises(ValueError, match="ring"):
        m.rotate_fragment(xyz, (0, 1, 2, 3), [{1, 3}, {0, 2}, {1, 3}, {0, 2}],
                          single_bonds={(0, 1), (1, 2), (2, 3), (0, 3)}, degrees=60)


def test_linear_dihedral_is_rejected():
    xyz = np.array([[0, 1, 0], [0, 0, 0], [1, 0, 0], [2, 0, 0]], dtype=float)
    with pytest.raises(ValueError, match="degenerate"):
        m.rotate_fragment(xyz, (0, 1, 2, 3), [{1}, {0, 2}, {1, 3}, {2}],
                          single_bonds={(0, 1), (1, 2), (2, 3)}, degrees=60)


def test_rigid_rotation_and_permuted_hydrogens_are_duplicates():
    symbols = ["O", "H", "H"]
    xyz = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
    rotated = xyz @ np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]]) + 4
    adj = [{1, 2}, {0}, {0}]
    assert m.equivalent_start(symbols, xyz, rotated[[0, 2, 1]], adj)


def test_all_atom_methyl_symmetry_with_fixed_lithium():
    symbols = ["C", "O", "Li", "H", "H", "H"]
    xyz = np.array([[0, 0, 0], [1.4, 0, 0], [1.5, 2, 2],
                    [-0.3, 1, 0], [-0.3, -0.5, 0.866025403784],
                    [-0.3, -0.5, -0.866025403784]])
    adj = [{1, 3, 4, 5}, {0}, set(), {0}, {0}, {0}]
    assert m.equivalent_start(symbols, xyz, xyz, adj)
    assert m.equivalent_start(symbols, xyz, xyz[[0, 1, 2, 4, 3, 5]], adj)
    rotated120 = m._rotate_about_axis(xyz, 0, 1, 120, moving_indices={0, 3, 4, 5})
    assert m.equivalent_start(symbols, xyz, rotated120, adj)
    reordered = np.array(rotated120)[[0, 1, 2, 4, 5, 3]]
    assert m.equivalent_start(symbols, xyz, reordered, adj)
    rotated60 = m._rotate_about_axis(xyz, 0, 1, 60, moving_indices={0, 3, 4, 5})
    assert not m.equivalent_start(symbols, xyz, rotated60, adj)


def test_repair_only_selected_members_and_keep_source_immutable(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    good = {"member_key": "DMC|LiM_2plus|tors_7_0_1_2", "name": "DMC",
            "slot": "LiM_2plus", "seed": "tors_7_0_1_2", "dihedral": "7-0-1-2"}
    bad = {"member_key": "EC|LiM_2plus|tors_2_3_4_10", "name": "EC",
           "slot": "LiM_2plus", "seed": "tors_2_3_4_10", "dihedral": "2-3-4-10"}
    extra = {"member_key": "AN|M_plus|unrequested", "name": "AN", "slot": "M_plus", "seed": "unrequested"}
    (source / "manifest.json").write_text(json.dumps({"members": [good, bad, extra]}), encoding="utf-8")
    (source / "batch_2.txt").write_text("tasks/DMC/LiM_2plus__tors_7_0_1_2\ntasks/EC/LiM_2plus__tors_2_3_4_10\n", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    monkeypatch.setattr(m, "_repair_member", lambda pkg, row, kept: (_ for _ in ()).throw(ValueError("multiple bond"))
                        if row["name"] == "EC" else {"member": row, "geometry": "1\nfixture\nH 0 0 0\n", "input": "fixture", "audit": {}})
    output = tmp_path / "repair"
    result = m.build_repair_package(source, output, batch=2)
    assert result["tasks"] == 1
    assert len(result["rejected"]) == 1
    assert result["members"][0]["member_key"] == good["member_key"]
    assert {p.name: p.read_bytes() for p in source.iterdir()} == before
    with pytest.raises(ValueError, match="exists"):
        m.build_repair_package(source, output, batch=2)
