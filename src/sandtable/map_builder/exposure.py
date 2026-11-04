"""Resolve editor exposure fields through an interchangeable core model."""

import copy
from sandtable.routing import RangeExposureModel


class MapExposureResolver:
    def __init__(self, model_factory=None):
        self.model_for = model_factory or RangeExposureModel.from_map

    def resolve(self, document):
        resolved = copy.deepcopy(document)
        model = self.model_for(resolved)
        nodes = {n["id"]: (n["x"], n["y"]) for n in resolved["nodes"]}
        for road in resolved["roads"]:
            road["exposure_auto"] = model.score([nodes[road["u"]], nodes[road["v"]]])
        return resolved
