class IndiaEncounterAdapter:
    def adapt(self, encounter_class: str, description: str) -> str:
        # PHC canonical types: OPD_NEW, OPD_FOLLOWUP, CHRONIC_REVIEW, REFERRAL_FOLLOWUP, ANTENATAL, IMMUNISATION, PREVENTIVE
        e_class = str(encounter_class).lower()
        desc = str(description).lower()
        
        if "pregnancy" in desc or "prenatal" in desc or "antenatal" in desc:
            return "ANTENATAL"
        if "vaccin" in desc or "immuniz" in desc or "immunis" in desc:
            return "IMMUNISATION"
        if "wellness" in e_class or "preventive" in desc:
            return "PREVENTIVE"
        if "chronic" in desc or "follow-up" in desc or "follow up" in desc:
            return "CHRONIC_REVIEW"
        if "ambulatory" in e_class or "outpatient" in e_class or "urgent" in e_class:
            return "OPD_NEW"
            
        return "RETAINED_SOURCE"
