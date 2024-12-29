import random


def _is_valid_assignment(source, target, exclusions):
    if source == target:
        return False
    if (source, target) in exclusions:
        return False
    return True


def _backtrack_assignments(participants, exclusions, assignments, targets):
    if not participants:
        return assignments

    source = participants[0]
    random.shuffle(targets)  # Shuffle targets to ensure randomness
    for target in targets:
        if _is_valid_assignment(source, target, exclusions):
            new_assignments = assignments + [(source, target)]
            new_targets = targets[:]
            new_targets.remove(target)
            result = _backtrack_assignments(
                participants[1:], exclusions, new_assignments, new_targets
            )
            if result:
                return result

    return None


def resolve_secret_santa(
    participants,
    exclusions,
):
    return _backtrack_assignments(participants, exclusions, [], participants[:])
