"""Stable function facade over independently testable application services."""

from sandtable.map_builder import Invalid, MapPlanningService
from sandtable.routing import RangeExposureModel, ExposurePenaltyCost
from sandtable.street_graph import StreetEdge
from .identity import canonical, digest
from .templates import default_config, blank_config
from .settings import MissionSettings
from .compiler import ScenarioCompiler
from .comparison import ComparisonDesigner
from .formation import FormationBuilder
from .paths import ViewerPaths

REPO = ViewerPaths.discover().repository


def compile_config(raw, load_target_kg=None):
    return ScenarioCompiler().compile(raw, load_target_kg)


def normalize_map(raw, draft_mode=False):
    return MapPlanningService().normalize(raw, draft_mode)


def route_graph(document):
    plan = MapPlanningService().plan(document)
    return plan.graph, plan.nodes, plan.route, plan.warnings


def normalize_mission(raw, draft_mode=False):
    return MissionSettings().normalize(raw, draft_mode)


def formation_preview(raw):
    return FormationBuilder().preview(raw)


def comparison_design(raw, design):
    return ComparisonDesigner().create(raw, design)


def import_config(raw):
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise Invalid("Expected a V3 schema_version=1 file.")
    name = raw.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 120:
        raise Invalid("Mission name must be 1-120 characters.")
    return dict(
        schema_version=1,
        name=name,
        map=normalize_map(raw.get("map"), True),
        mission=normalize_mission(raw.get("mission"), True),
    )
