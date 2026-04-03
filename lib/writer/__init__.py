from .agents import BookLayout, DraftChapterSegment, GenerateChapterSegment, LayoutChapter, RefinetChapter
from lib.io import (
	build_snapshot_manager,
	build_snapshot_manager_from_files,
	FileSnapshotManager,
	MongoSnapshotManager,
)
from lib.io.factory import (
	infer_app_config_path,
	normalize_snapshot_type,
	resolve_snapshot_type,
)
from ..io.manager import SnapshotManager as AbstractSnapshotManager
from lib.models import ChapterConfig, ChapterSnapshot, RuntimeWorkspaceState, SnapshotConfig, WorkspaceSnapshot
from .writables import ChapterSegmentText, DraftedSegmentPrompt, ProjectSettings, SegmentBlueprint
from .write import publish_book_content, write_authored_content, write_dummy_content, write_generated_content

SnapshotManager = FileSnapshotManager

__all__ = [
	"ChapterConfig",
	"ChapterSnapshot",
	"SnapshotConfig",
	"SnapshotManager",
	"AbstractSnapshotManager",
	"FileSnapshotManager",
	"MongoSnapshotManager",
	"BookLayout",
	"RefinetChapter",
	"LayoutChapter",
	"DraftChapterSegment",
	"GenerateChapterSegment",
	"SegmentBlueprint",
	"DraftedSegmentPrompt",
	"ChapterSegmentText",
	"ProjectSettings",
	"WorkspaceSnapshot",
	"RuntimeWorkspaceState",
	"publish_book_content",
	"write_authored_content",
	"write_dummy_content",
	"write_generated_content",
	"normalize_snapshot_type",
	"infer_app_config_path",
	"resolve_snapshot_type",
	"build_snapshot_manager",
	"build_snapshot_manager_from_files",
]