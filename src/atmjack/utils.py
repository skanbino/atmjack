"""
Single-service rule processing functions
"""

import copy


def recurse(all_info, current_info, target_path, current_path, config, add_suffix=False):
    """
    Recursively test conditions for a path.
    In order to do this, needs to evaluate all the `id` possibilities.

    When the value in the path is `id`, this represents either a key for a dict or an index for a list.

    When the is `id`:
    - For a dict return value at key
    - For a list, return the list
    When the value ends in `id.`:
    - For a dict, return a list of keys
    - For a list, return value at the index indicated by id
    `
    :param all_info:        All of the services' data
    :param current_info:    ?
    :param target_path:     The path that is being tested
    :param current_path:
    :param config:          The Rule object that is being tested
    :param add_suffix:      ?
    :return:
    """
    results = []
    if len(target_path) == 0:
        # Dashboard: count the number of processed resources here
        config.checked_items = config.checked_items + 1
        # Test for conditions...
        if pass_conditions(all_info, current_path, copy.deepcopy(config.conditions)):
            # id_suffix
            if add_suffix and hasattr(config, "id_suffix"):
                suffix = fix_path_string(all_info, current_path, config.id_suffix)
                current_path.append(suffix)
            # class_suffix
            if add_suffix and hasattr(config, "class_suffix"):
                suffix = fix_path_string(all_info, current_path, config.class_suffix)
                current_path.append(suffix)
            results.append(".".join(current_path))
        # Return the flagged items...
        return results
    target_path = copy.deepcopy(target_path)
    dbg_target_path = copy.deepcopy(target_path)
    current_path = copy.deepcopy(current_path)
    attribute = target_path.pop(0)
    if isinstance(current_info, dict):
        if attribute in current_info:
            split_path = copy.deepcopy(current_path)
            split_path.append(attribute)
            results = results + recurse(all_info, current_info[attribute], target_path, split_path, config, add_suffix)
        elif attribute == "id":
            for key in current_info:
                split_target_path = copy.deepcopy(target_path)
                split_current_path = copy.deepcopy(current_path)
                split_current_path.append(key)
                split_current_info = current_info[key]
                results = results + recurse(
                    all_info, split_current_info, split_target_path, split_current_path, config, add_suffix
                )
    # To handle lists properly, I would have to make sure the list is properly ordered and I can use the index to
    # consistently access an object... Investigate (or do not use lists)
    elif isinstance(current_info, list):
        for index, split_current_info in enumerate(current_info):
            split_current_path = copy.deepcopy(current_path)
            split_current_path.append(str(index))
            results = results + recurse(
                all_info, split_current_info, copy.deepcopy(target_path), split_current_path, config, add_suffix
            )
    # Python 2-3 compatible way to check for string type
    elif isinstance(current_info, str):
        split_current_path = copy.deepcopy(current_path)
        results = results + recurse(all_info, current_info, [], split_current_path, config, add_suffix)
    else:
        print_exception(
            f"Unable to recursively test condition for path {current_path}: "
            f'unhandled case for "{type(current_info)}" type',
            additional_details={
                "current_path": current_path,
                "current_info": current_info,
                "dbg_target_path": dbg_target_path,
            },
        )
    return results


def fix_path_string(all_info, path, string) -> str:
    """Local replacement for ScoutSuite.core.conditions.fix_path_string."""
    return str(string).replace("/", ".")


def pass_conditions(all_info, path, conditions=None) -> bool:
    """Minimal local replacement for ScoutSuite.core.conditions.pass_conditions."""
    if conditions is None:
        return True
    if isinstance(conditions, list):
        return all(pass_conditions(all_info, path, c) for c in conditions)
    return bool(conditions)


def print_exception(message: str, additional_details=None) -> None:
    """Local replacement for ScoutSuite.core.console.print_exception."""
    print(f"[!] {message}")
    if additional_details:
        print(f" {additional_details}")


def do_something_useful() -> None:
    """Placeholder invoked by cli.py."""
    print("atmjack ready")
