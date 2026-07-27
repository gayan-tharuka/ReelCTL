"""Duplicate media detection for ReelCTL.

Identifies duplicate copies of the same movie or TV episode and recommends
which to keep based on quality comparison.
"""

from __future__ import annotations

from collections import defaultdict

from loguru import logger

from reelctl.models import DuplicateGroup, MediaIdentity, MediaType
from reelctl.normalizer import quality_score


def detect_duplicates(identities: list[MediaIdentity]) -> list[DuplicateGroup]:
    """Find groups of duplicate media files.

    Groups files by TMDB ID (if available) or by normalized title + year.
    Within each group, recommends the highest quality file to keep.

    Args:
        identities: List of identified media files.

    Returns:
        List of DuplicateGroup objects (only groups with 2+ files).
    """
    # Group by a unique identity key
    groups: dict[str, list[MediaIdentity]] = defaultdict(list)

    for identity in identities:
        if identity.media_type == MediaType.UNKNOWN:
            continue

        key = _make_group_key(identity)
        groups[key].append(identity)

    # Filter to groups with duplicates
    duplicate_groups: list[DuplicateGroup] = []

    for key, members in groups.items():
        if len(members) < 2:
            continue

        # Sort by quality (best first)
        members.sort(
            key=lambda m: quality_score(m.quality, m.source),
            reverse=True,
        )

        best = members[0]
        rest = members[1:]

        group = DuplicateGroup(
            title=best.title,
            year=best.year,
            tmdb_id=best.tmdb_id,
            files=members,
            recommended_keep=best,
            recommended_delete=rest,
        )
        duplicate_groups.append(group)

        logger.info(
            "Duplicate group: '{}' — keep [{}] {}, delete {} others",
            best.title,
            best.quality or "?",
            best.source or "?",
            len(rest),
        )

    if duplicate_groups:
        logger.info("Found {} duplicate groups", len(duplicate_groups))

    return duplicate_groups


def _make_group_key(identity: MediaIdentity) -> str:
    """Create a grouping key for duplicate detection.

    Uses TMDB ID when available for accuracy, falls back to
    normalized title + year + season + episode.
    """
    if identity.tmdb_id:
        base = f"tmdb:{identity.tmdb_id}"
    else:
        base = f"title:{identity.title.lower().strip()}"
        if identity.year:
            base += f":{identity.year}"

    # For TV, include season + episode to avoid grouping different episodes
    if identity.media_type == MediaType.TV:
        base += f":s{identity.season or 0}e{identity.episode or 0}"

    return base
