"""User profile manager."""

import os
import json
from typing import Optional
from datetime import datetime

from config import get_settings
from schemas.models import UserProfile, OnboardingStage, Language


class ProfileManager:
    """Manages user profiles and onboarding state."""

    def __init__(self):
        settings = get_settings()
        self.data_dir = os.path.join(settings.data_dir, "profiles")
        os.makedirs(self.data_dir, exist_ok=True)

        # In-memory cache
        self._profiles: dict[str, UserProfile] = {}

    def _get_file_path(self, user_id: str) -> str:
        """Get file path for user's profile."""
        return os.path.join(self.data_dir, f"{user_id}_profile.json")

    def _load_profile(self, user_id: str) -> UserProfile:
        """Load user profile from disk."""
        file_path = self._get_file_path(user_id)

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert enums
                data["onboarding_stage"] = OnboardingStage(data.get("onboarding_stage", "not_started"))
                data["preferred_language"] = Language(data.get("preferred_language", "ru"))
                if data.get("created_at"):
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                return UserProfile(**data)

        # Create new profile
        return UserProfile(user_id=user_id)

    def _save_profile(self, profile: UserProfile):
        """Save user profile to disk."""
        file_path = self._get_file_path(profile.user_id)

        data = {
            "user_id": profile.user_id,
            "name": profile.name,
            "preferred_name": profile.preferred_name,
            "created_at": profile.created_at.isoformat(),
            "onboarding_stage": profile.onboarding_stage.value,
            "onboarding_day": profile.onboarding_day,
            "preferred_language": profile.preferred_language.value,
            "wake_time": profile.wake_time,
            "peak_productivity_time": profile.peak_productivity_time,
            "motivation_style": profile.motivation_style,
            "energy_patterns": profile.energy_patterns,
            "effective_approaches": profile.effective_approaches,
            "ineffective_approaches": profile.ineffective_approaches,
            "personal_notes": profile.personal_notes
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_profile(self, user_id: str) -> UserProfile:
        """Get user profile, creating if doesn't exist."""
        if user_id not in self._profiles:
            self._profiles[user_id] = self._load_profile(user_id)
        return self._profiles[user_id]

    def save_profile(self, profile: UserProfile):
        """Save profile to cache and disk."""
        self._profiles[profile.user_id] = profile
        self._save_profile(profile)

    def update_name(self, user_id: str, name: str, preferred_name: str = None):
        """Update user's name."""
        profile = self.get_profile(user_id)
        profile.name = name
        if preferred_name:
            profile.preferred_name = preferred_name
        self.save_profile(profile)

    def advance_onboarding(self, user_id: str, stage: OnboardingStage):
        """Advance onboarding to next stage."""
        profile = self.get_profile(user_id)
        profile.onboarding_stage = stage

        # Track days for settling_in period
        if stage == OnboardingStage.SETTLING_IN:
            profile.onboarding_day = 1
        elif stage == OnboardingStage.FULL:
            profile.onboarding_day = 0

        self.save_profile(profile)

    def increment_onboarding_day(self, user_id: str):
        """Increment onboarding day counter."""
        profile = self.get_profile(user_id)

        if profile.onboarding_stage == OnboardingStage.SETTLING_IN:
            profile.onboarding_day += 1

            # After 5 days, move to full mode
            if profile.onboarding_day > 5:
                profile.onboarding_stage = OnboardingStage.FULL
                profile.onboarding_day = 0

            self.save_profile(profile)

    def add_effective_approach(self, user_id: str, approach: str):
        """Record that a motivation approach worked."""
        profile = self.get_profile(user_id)
        if approach not in profile.effective_approaches:
            profile.effective_approaches.append(approach)
        # Remove from ineffective if was there
        if approach in profile.ineffective_approaches:
            profile.ineffective_approaches.remove(approach)
        self.save_profile(profile)

    def add_ineffective_approach(self, user_id: str, approach: str):
        """Record that a motivation approach didn't work."""
        profile = self.get_profile(user_id)
        if approach not in profile.ineffective_approaches:
            profile.ineffective_approaches.append(approach)
        self.save_profile(profile)

    def add_personal_note(self, user_id: str, note: str):
        """Add a note about the user."""
        profile = self.get_profile(user_id)
        profile.personal_notes.append(f"[{datetime.now().strftime('%Y-%m-%d')}] {note}")
        # Keep only last 50 notes
        profile.personal_notes = profile.personal_notes[-50:]
        self.save_profile(profile)

    def delete_profile(self, user_id: str):
        """Delete user profile."""
        if user_id in self._profiles:
            del self._profiles[user_id]

        file_path = self._get_file_path(user_id)
        if os.path.exists(file_path):
            os.unlink(file_path)


# Singleton instance
_profile_manager = None


def get_profile_manager() -> ProfileManager:
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager
