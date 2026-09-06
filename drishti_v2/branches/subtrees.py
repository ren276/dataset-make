"""
drishti_v2/branches/subtrees.py
=================================
Shared sub-trees (questionnaire-tree-design-memo.md section 5, point 1):
"Cross-links are references, never copies." RASH_MORPH_NODES is authored
once and is the literal tail of the `rash` branch's own node graph AND the
subtree spliced into `fever` at FV-S1 -- the same Python dict object is used
both places, so there is exactly one place that defines what "rash
morphology" means.

FEVER_QUAL is a separate, smaller object: the memo names it explicitly as
"FEVER-QUAL -- FV-01, FV-02, FV-06 only", a deliberately abbreviated subset
of the fever branch's own (longer) FV-01/02/06 sequence. Because the DAG
position differs (the abbreviated chain returns after FV-06 instead of
continuing to FV-03), it cannot be the literal same Node objects as fever's
main-line FV-01/FV-02/FV-06 -- their `.next` wiring differs by construction.
What IS shared, and is the part the memo actually cares about for dataset
contract purposes, is the nodeId (and therefore fieldId, options and answer
model entries): FEVER_QUAL's "FV-01" resolves against the exact same
AnswerModel entries as fever's own "FV-01", because AnswerModel is keyed by
nodeId, not by which branch embeds the node. One authored question, one
answer model, reused; only the local next-pointer is context-specific. This
is a build decision (the memo does not spell out how two objects can share
a nodeId across branches at the code level) and is stated here rather than
left implicit.
"""

from __future__ import annotations

from ..schema import AnswerOption, GatewayNode, QuestionNode, TerminalNode, contains, equals, value_of

_ASSUMED = {"sourceType": "ASSUMED", "source": "No Indian unknown-rate survey exists; "
            "declared low and flat across nodes.", "declaredOn": "2026-09-06"}


def _no_unknown(rate=0.03):
    return dict(unknown_rate=rate, unknown_provenance=_ASSUMED)


# ---------------------------------------------------------------------------
# RASH-MORPH: RSH-03 .. RSH-09 (tree memo section 5)
# ---------------------------------------------------------------------------

def _gw_rsh_emg1(fields, ctx):
    return contains(fields, "danger_signs", "ds_purpura") or equals(fields, "rash_morphology", "rm_purple_spots")


def _gw_rsh_emg2(fields, ctx):
    mucosal = contains(fields, "danger_signs", "ds_mucosal") or contains(fields, "danger_signs", "ds_skin_peeling")
    blister_drug = equals(fields, "rash_morphology", "rm_fluid_blister") and equals(fields, "new_drug_2_weeks", "nd_yes")
    return mucosal or blister_drug


def _gw_rsh_urg1(fields, ctx):
    leprosy_patch = equals(fields, "rash_morphology", "rm_pale_patch") and equals(
        fields, "hypopigmented_patch_sensation", "hp_reduced")
    return leprosy_patch or equals(fields, "rash_symptom", "rs_numb")


RASH_MORPH_NODES = {
    "RSH-03": QuestionNode(
        nodeId="RSH-03", fieldId="rash_distribution", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rdst_face_first", "Started on the face, spread down", next="RSH-04"),
            AnswerOption("rdst_trunk", "Mainly on the chest, back or stomach", next="RSH-04"),
            AnswerOption("rdst_limbs", "Mainly on the arms or legs", next="RSH-04"),
            AnswerOption("rdst_palms_soles", "Includes palms or soles", next="RSH-04"),
            AnswerOption("rdst_whole_body", "All over the body", next="RSH-04"),
            AnswerOption("rdst_one_patch", "One patch or a few patches only", next="RSH-04"),
        ],
        default_next="RSH-04", unknown_option="rdst_unknown", **_no_unknown(0.05),
    ),
    "RSH-04": QuestionNode(
        nodeId="RSH-04", fieldId="rash_morphology", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rm_flat_red", "Flat red spots", next="RSH-05"),
            AnswerOption("rm_raised", "Raised bumps", next="RSH-05"),
            AnswerOption("rm_fluid_blister", "Fluid-filled blisters", next="RSH-G1"),
            AnswerOption("rm_pustular", "Pus-filled spots", next="RSH-05"),
            AnswerOption("rm_scaly_patch", "Dry, scaly patch", next="RSH-05"),
            AnswerOption("rm_pale_patch", "Pale / lighter-coloured patch", next="RSH-06"),
            AnswerOption("rm_purple_spots", "Purple or red spots that do not fade", next="RSH-G1"),
        ],
        default_next="RSH-05", unknown_option="rm_unknown", **_no_unknown(0.04),
    ),
    # RSH-04 checkpoint: both EMG-1 (rm_purple_spots) and the rash_morphology
    # half of EMG-2 (rm_fluid_blister; new_drug_2_weeks not yet known here, so
    # this is a safe partial evaluation -- the full EMG-2 rule is re-checked
    # at "RSH-G3" once new_drug_2_weeks is answered).
    "RSH-G1": GatewayNode("RSH-G1", "GW-RSH-EMG-1", _gw_rsh_emg1, next="RSH-G1b",
                           raisesTo="REFER_EMERGENCY",
                           severeConditions=["meningococcaemia", "severe dengue"]),
    "RSH-G1b": GatewayNode("RSH-G1b", "GW-RSH-EMG-2", _gw_rsh_emg2, next="RSH-05",
                            raisesTo="REFER_EMERGENCY", severeConditions=["SJS / TEN"]),
    "RSH-05": QuestionNode(
        nodeId="RSH-05", fieldId="rash_symptom", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("rs_itchy", "Itchy", next="RSH-07"),
            AnswerOption("rs_painful", "Painful", next="RSH-07"),
            AnswerOption("rs_burning", "Burning", next="RSH-07"),
            AnswerOption("rs_numb", "No feeling in it", next="RSH-G2"),
            AnswerOption("rs_none", "Neither", next="RSH-07"),
        ],
        default_next="RSH-07", unknown_option="rs_unknown", **_no_unknown(0.04),
    ),
    "RSH-G2": GatewayNode("RSH-G2", "GW-RSH-URG-1", _gw_rsh_urg1, next="RSH-07",
                           raisesTo="REFER_URGENT", severeConditions=["leprosy"]),
    "RSH-06": QuestionNode(
        nodeId="RSH-06", fieldId="hypopigmented_patch_sensation", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("hp_normal_sensation", "Feels the same", next="RSH-07"),
            AnswerOption("hp_reduced", "Feels less, or nothing", next="RSH-G2"),
        ],
        default_next="RSH-07", unknown_option="hp_unknown", **_no_unknown(0.06),
        guard=lambda fields: equals(fields, "rash_morphology", "rm_pale_patch"),
    ),
    "RSH-07": QuestionNode(
        nodeId="RSH-07", fieldId="new_drug_2_weeks", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("nd_yes", "Yes", next="RSH-G3"),
            AnswerOption("nd_no", "No", next="RSH-08"),
        ],
        default_next="RSH-08", unknown_option="nd_unknown", **_no_unknown(0.03),
    ),
    # Full re-check of EMG-2 now that new_drug_2_weeks is known (only this half
    # of the OR can newly become true here; EMG-1 does not depend on this field).
    "RSH-G3": GatewayNode("RSH-G3", "GW-RSH-EMG-2", _gw_rsh_emg2, next="RSH-08",
                           raisesTo="REFER_EMERGENCY", severeConditions=["SJS / TEN"]),
    "RSH-08": QuestionNode(
        nodeId="RSH-08", fieldId="household_others_affected", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ho_yes", "Yes", next="RSH-09"),
            AnswerOption("ho_no", "No", next="RSH-09"),
        ],
        default_next="RSH-09", unknown_option="ho_unknown", **_no_unknown(0.05),
    ),
    "RSH-09": QuestionNode(
        nodeId="RSH-09", fieldId="attachment_photo_present", answerType="SINGLE_CHOICE",
        options=[
            AnswerOption("ph_taken", "Photo taken", next="RSH-END"),
            AnswerOption("ph_declined", "Patient did not consent", next="RSH-END"),
            AnswerOption("ph_not_possible", "Cannot take a photo now", next="RSH-END"),
        ],
        default_next="RSH-END", unknown_option="ph_not_possible", **_no_unknown(0.0),
    ),
    "RSH-END": TerminalNode("RSH-END"),
}


# ---------------------------------------------------------------------------
# FEVER-QUAL: abbreviated FV-01, FV-02, FV-06 (see module docstring)
# ---------------------------------------------------------------------------

def _gw_fev_emg3_bleeding_only(fields, ctx):
    return not (value_of(fields, "bleeding_manifestation") in (None, frozenset({"bl_none"}), frozenset({"bl_unknown"})))


def make_fever_qual_nodes() -> dict:
    """A fixed DAG ending at its own TerminalNode ('FV-QUAL-END'). The walker
    pops back to whatever SubtreeRefNode.returnNext the caller declared when
    it reaches that terminal -- a GatewayNode.next can only point at a node
    inside its OWN node_dict, never at the enclosing branch's node, so the
    subtree must end on a real TerminalNode rather than have its last
    gateway point directly at the parent's return target."""
    return {
        "FV-01": QuestionNode(
            nodeId="FV-01", fieldId="fever_duration_band", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("fd_today", "Today only", next="FV-02"),
                AnswerOption("fd_1_3", "1 to 3 days", next="FV-02"),
                AnswerOption("fd_4_7", "4 to 7 days", next="FV-02"),
                AnswerOption("fd_8_14", "8 to 14 days", next="FV-02"),
                AnswerOption("fd_gt_14", "More than 14 days", next="FV-02"),
            ],
            default_next="FV-02", unknown_option="fd_unknown", **_no_unknown(0.03),
        ),
        "FV-02": QuestionNode(
            nodeId="FV-02", fieldId="fever_pattern", answerType="SINGLE_CHOICE",
            options=[
                AnswerOption("fp_stepladder", "Rising a little more each day, does not fully settle",
                             next="FV-06", valueToken="stepladder fever"),
                AnswerOption("fp_cyclical", "Comes and goes, with shaking chills",
                             next="FV-06", valueToken="cyclical high fever with chills"),
                AnswerOption("fp_evening", "Rises in the evening or at night",
                             next="FV-06", valueToken="evening fever"),
                AnswerOption("fp_continuous", "High and continuous, no clear pattern",
                             next="FV-06", valueToken="high fever"),
                AnswerOption("fp_mild", "Low-grade throughout", next="FV-06", valueToken="mild fever"),
            ],
            default_next="FV-06", unknown_option="fp_unknown", **_no_unknown(0.03),
        ),
        "FV-06": QuestionNode(
            nodeId="FV-06", fieldId="bleeding_manifestation", answerType="MULTI_CHOICE",
            options=[
                AnswerOption("bl_gums", "Bleeding gums", next="FV-QUAL-G3"),
                AnswerOption("bl_nose", "Nose bleed", next="FV-QUAL-G3"),
                AnswerOption("bl_skin", "Red or purple spots under skin", next="FV-QUAL-G3"),
                AnswerOption("bl_vomit", "Blood in vomit", next="FV-QUAL-G3"),
                AnswerOption("bl_stool", "Black or bloody stool", next="FV-QUAL-G3"),
                AnswerOption("bl_urine", "Blood in urine", next="FV-QUAL-G3"),
            ],
            default_next="FV-QUAL-G3", unknown_option="bl_unknown", none_option="bl_none",
            **_no_unknown(0.02),
        ),
        "FV-QUAL-G3": GatewayNode("FV-QUAL-G3", "GW-FEV-EMG-3", _gw_fev_emg3_bleeding_only,
                                   next="FV-QUAL-END", routeTo="emergency_heavy_bleeding",
                                   severeConditions=["severe dengue", "sepsis with DIC"]),
        "FV-QUAL-END": TerminalNode("FV-QUAL-END"),
    }
