import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "tsrkit_pvm", "common")
)

import extended

ExtendedList = extended.ExtendedList


def test_basic_functionality():
    """Test that ExtendedList works like a normal list for in-bounds access"""
    ext_list = ExtendedList([1, 2, 3, 4, 5])

    # Test normal indexing
    assert ext_list[0] == 1
    assert ext_list[2] == 3
    assert ext_list[-1] == 5
    assert ext_list[-2] == 4

    # Test length
    assert len(ext_list) == 5

    # Test iteration
    assert list(ext_list) == [1, 2, 3, 4, 5]


def test_out_of_bounds_access():
    """Test out-of-bounds access returns default value"""
    # Test with default None
    ext_list = ExtendedList([1, 2, 3])

    # Test positive out-of-bounds
    assert ext_list[5] is None
    assert ext_list[10] is None

    # Test negative out-of-bounds
    assert ext_list[-10] is None

    # Test with custom default
    ext_list_custom = ExtendedList([1, 2, 3], default=-1)
    assert ext_list_custom[5] == -1
    assert ext_list_custom[10] == -1
    assert ext_list_custom[-10] == -1


def test_slice_operations():
    """Test slice operations work correctly"""
    ext_list = ExtendedList([1, 2, 3, 4, 5], default=0)

    # Test normal slicing
    assert ext_list[1:4] == [2, 3, 4]
    assert ext_list[:3] == [1, 2, 3]
    assert ext_list[2:] == [3, 4, 5]

    # Test slicing with step
    assert ext_list[::2] == [1, 3, 5]
    assert ext_list[1::2] == [2, 4]

    # Test slice that goes out of bounds (should work normally with slice.indices)
    assert ext_list[3:10] == [4, 5]
    assert ext_list[-2:10] == [4, 5]
