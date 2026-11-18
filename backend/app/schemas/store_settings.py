from pydantic import BaseModel, ConfigDict, Field


class StoreSettingsUpdate(BaseModel):

    max_assignees_per_task: int | None = Field(default=None, ge=0)
    operational_checklists_enabled: bool | None = None
    auto_logout_minutes: int | None = Field(default=None, ge=1)
    hide_task_timer: bool | None = None
    require_live_photo_only: bool | None = None
    require_pin_on_complete: bool | None = None
    enable_audio_alerts: bool | None = None
    shifts: list[str] | None = Field(default=None, min_length=1)


class StoreSettingsPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    store_id: int
    max_assignees_per_task: int | None
    operational_checklists_enabled: bool
    auto_logout_minutes: int
    hide_task_timer: bool
    require_live_photo_only: bool
    require_pin_on_complete: bool
    enable_audio_alerts: bool
    shifts: list[str]
