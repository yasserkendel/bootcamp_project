from __future__ import annotations
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import ifcopenshell.util.shape_builder

class IFCGenerator:
    def __init__(self, specs: dict[str, Any], output_dir: Path):
        self.specs = specs
        self.output_dir = output_dir
        self.dims = specs["dimensions"]
        self.part = specs["part"]
        self.mech = specs["mechanical"]
        self.mats = specs["materials"]

    @staticmethod
    def _pt2(x: float, y: float):
        return (float(x), float(y))

    @staticmethod
    def _pt3(x: float, y: float, z: float):
        return (float(x), float(y), float(z))

    @staticmethod
    def _dir3(x: float, y: float, z: float):
        return (float(x), float(y), float(z))

    def generate(self) -> Path:
        model = ifcopenshell.file(schema="IFC4")

        project = ifcopenshell.api.run(
            "root.create_entity", model,
            ifc_class="IfcProject",
            name=f"INDUSTRIE IA — {self.part['reference']}"
        )
        ifcopenshell.api.run("unit.assign_unit", model,
                             length={"is_metric": True, "raw": "MILLIMETRES"},
                             area={"is_metric": True, "raw": "SQUARE_METRES"},
                             volume={"is_metric": True, "raw": "CUBIC_METRES"})

        context = ifcopenshell.api.run("context.add_context", model, context_type="Model")
        body_ctx = ifcopenshell.api.run(
            "context.add_context", model,
            context_type="Model",
            context_identifier="Body",
            target_view="MODEL_VIEW",
            parent=context,
        )

        site     = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite",          name="Site industriel")
        building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding",       name="Atelier de fabrication")
        storey   = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Niveau 0")

        # These use plural 'products'
        ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project,  products=[site])
        ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site,     products=[building])
        ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

        valve_body   = self._create_valve_body(model, body_ctx, storey)
        left_flange  = self._create_flange(model, body_ctx, storey, offset_x=0.0, label="Bride gauche")
        right_flange = self._create_flange(model, body_ctx, storey, offset_x=float(self.dims["face_to_face_mm"]), label="Bride droite")
        stem         = self._create_stem(model, body_ctx, storey)

        self._assign_materials(model, [valve_body, left_flange, right_flange, stem])
        self._add_property_sets(model, valve_body)

        output_path = self.output_dir / f"{self.part['reference']}_3d.ifc"
        model.write(str(output_path))
        return output_path

    def _create_valve_body(self, model, body_ctx, storey):
        d, f2f, bore = self.dims, float(self.dims["face_to_face_mm"]), float(self.dims["bore_diameter_mm"])
        od = float(d["flange_od_mm"]) * 0.75
        outer = model.createIfcCircleProfileDef("AREA", None, model.createIfcAxis2Placement2D(model.createIfcCartesianPoint(self._pt2(0,0)), None), od/2)
        inner = model.createIfcCircleProfileDef("AREA", None, model.createIfcAxis2Placement2D(model.createIfcCartesianPoint(self._pt2(0,0)), None), bore/2)
        composite = model.createIfcCompositeProfileDef("AREA", "ValveBodyProfile", [outer, inner])
        solid = model.createIfcExtrudedAreaSolid(composite, 
            model.createIfcAxis2Placement3D(model.createIfcCartesianPoint(self._pt3(0,0,0)), model.createIfcDirection(self._dir3(0,0,1)), model.createIfcDirection(self._dir3(1,0,0))),
            model.createIfcDirection(self._dir3(0,0,1)), f2f)
        valve = self._make_product(model, body_ctx, ifc_class="IfcFlowFitting", name=self.part["name"], solid=solid, position=self._pt3(0,0,0))
        ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[valve])
        return valve

    def _create_flange(self, model, body_ctx, storey, offset_x: float, label: str):
        flange_od, bore, thick = float(self.dims["flange_od_mm"]), float(self.dims["bore_diameter_mm"]), float(self.dims["flange_thickness_mm"])
        outer = model.createIfcCircleProfileDef("AREA", None, model.createIfcAxis2Placement2D(model.createIfcCartesianPoint(self._pt2(0,0)), None), flange_od/2)
        inner = model.createIfcCircleProfileDef("AREA", None, model.createIfcAxis2Placement2D(model.createIfcCartesianPoint(self._pt2(0,0)), None), bore/2)
        profile = model.createIfcCompositeProfileDef("AREA", f"{label}Profile", [outer, inner])
        solid = model.createIfcExtrudedAreaSolid(profile, 
            model.createIfcAxis2Placement3D(model.createIfcCartesianPoint(self._pt3(0,0,0)), model.createIfcDirection(self._dir3(0,0,1)), model.createIfcDirection(self._dir3(1,0,0))),
            model.createIfcDirection(self._dir3(0,0,1)), thick)
        x_pos = 0.0 if offset_x == 0.0 else offset_x - thick
        flange = self._make_product(model, body_ctx, ifc_class="IfcFlowFitting", name=label, solid=solid, position=self._pt3(x_pos, 0, 0))
        ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[flange])
        return flange

    def _create_stem(self, model, body_ctx, storey):
        stem_d, f2f, body_h = float(self.dims["stem_diameter_mm"]), float(self.dims["face_to_face_mm"]), float(self.dims["body_height_mm"])
        profile = model.createIfcCircleProfileDef("AREA", "StemProfile", model.createIfcAxis2Placement2D(model.createIfcCartesianPoint(self._pt2(0,0)), None), stem_d/2)
        solid = model.createIfcExtrudedAreaSolid(profile, 
            model.createIfcAxis2Placement3D(model.createIfcCartesianPoint(self._pt3(f2f/2, 0, body_h/2)), model.createIfcDirection(self._dir3(0,1,0)), model.createIfcDirection(self._dir3(1,0,0))),
            model.createIfcDirection(self._dir3(0,0,1)), 60.0)
        stem = self._make_product(model, body_ctx, ifc_class="IfcMember", name="Tige de vanne", solid=solid, position=self._pt3(0,0,0))
        ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[stem])
        return stem

    def _make_product(self, model, body_ctx, *, ifc_class, name, solid, position):
        shape_rep = model.createIfcShapeRepresentation(body_ctx, "Body", "SweptSolid", [solid])
        product_shape = model.createIfcProductDefinitionShape(None, None, [shape_rep])
        entity = ifcopenshell.api.run("root.create_entity", model, ifc_class=ifc_class, name=name)
        entity.Representation, entity.ObjectPlacement = product_shape, model.createIfcLocalPlacement(None, model.createIfcAxis2Placement3D(model.createIfcCartesianPoint(position), None, None))
        return entity

    def _assign_materials(self, model, elements):
        material = ifcopenshell.api.run("material.add_material", model, name=self.mats["body"], category="Metal")
        for el in elements:
            ifcopenshell.api.run("material.assign_material", model, products=[el], material=material)


    def _add_property_sets(self, model, valve_element):
        m, d, p = self.mech, self.dims, self.part
        
        # CHANGE 1: product (singular) instead of products
        pset = ifcopenshell.api.run("pset.add_pset", model,
                                    product=valve_element,
                                    name="Pset_ValveTypeCommon")
        
        ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={
            "Reference": p["reference"],
            "Status": "NEW",
            "ValvePattern": p["type"],
            "ValveMechanism": "GATE",
            "CloseOffRating": float(m["nominal_pressure_bar"]),
        })

        # CHANGE 2: product (singular) instead of products
        pset_mech = ifcopenshell.api.run("pset.add_pset", model,
                                         product=valve_element,
                                         name="Pset_IndustrieIA_Mechanical")
        
        ifcopenshell.api.run("pset.edit_pset", model, pset=pset_mech, properties={
            "NominalDiameter_mm": float(d["nominal_diameter_mm"]),
            "NominalPressure_bar": float(m["nominal_pressure_bar"]),
            "TestPressure_bar": float(m["test_pressure_bar"]),
            "MaxTemperature_C": float(m["max_temperature_c"]),
            "MinTemperature_C": float(m["min_temperature_c"]),
            "BodyMaterial": self.mats["body"],
            "StemMaterial": self.mats["stem"],
            "SeatMaterial": self.mats["seat"],
            "Standard": p["standard"],
            "FaceToFace_mm": float(d["face_to_face_mm"]),
            "FlangeOD_mm": float(d["flange_od_mm"]),
            "BoltCircle_mm": float(d["bolt_circle_diameter_mm"]),
            "NbBolts": int(d["bolt_holes"]),
        })