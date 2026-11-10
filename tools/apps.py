from django.apps import AppConfig
from django.conf import settings

MODULE_NAME = "tools"

DEFAULT_CFG = {
    "registers_perms": ["131000"],
    "registers_diagnoses_perms": ["131000", "131002", "131001"],  # TODO: check rights
    "registers_health_facilities_perms": ["131000", "131004", "131003"],  # TODO: check rights
    "registers_locations_perms": ["131000", "131006", "131005"],  # TODO: check rights
    "registers_items_perms": ["131000", "131008", "131007"],  # TODO: check rights
    "registers_services_perms": ["131000", "131010", "131009"],  # TODO: check rights
    # Download (query) and upload (write) of a register are guarded separately,
    # with one right each (reference DJANGO_PERMS: odd = query, even = write).
    # The stacked lists above stay for compatibility: a deployment overriding them
    # in ModuleConfiguration keeps its rule (see ToolsConfig.__load_config).
    "registers_diagnoses_query_perms": ["131001"],
    "registers_diagnoses_write_perms": ["131002"],
    "registers_health_facilities_query_perms": ["131003"],
    "registers_health_facilities_write_perms": ["131004"],
    "registers_locations_query_perms": ["131005"],
    "registers_locations_write_perms": ["131006"],
    "registers_items_query_perms": ["131007"],
    "registers_items_write_perms": ["131008"],
    "registers_services_query_perms": ["131009"],
    "registers_services_write_perms": ["131010"],
    # Extracts: an empty list made has_perms([]) True for everyone (anonymous
    # included). Reference ids (openimis-dev-tools tools/apps.py DJANGO_PERMS).
    "extracts_master_data_perms": ["131101"],
    "extracts_officer_feedbacks_perms": ["131106"],
    "extracts_officer_renewals_perms": ["131105"],
    # reference: 131102 OR 131103; has_perms is AND here, so only the catalogued one
    "extracts_phone_extract_perms": ["131103"],
    "extracts_upload_claims_perms": ["131104"],
    "master_data_password": None,
}


def _overridden_keys(cfg):
    """Keys of `cfg` whose value differs from the shipped default, i.e. set by the deployment."""
    return {k for k, v in cfg.items() if DEFAULT_CFG.get(k, object()) != v}


class ToolsConfig(AppConfig):
    name = MODULE_NAME
    registers_perms = []
    registers_diagnoses_perms = []
    registers_health_facilities_perms = []
    registers_locations_perms = []
    registers_items_perms = []
    registers_services_perms = []
    registers_diagnoses_query_perms = []
    registers_diagnoses_write_perms = []
    registers_health_facilities_query_perms = []
    registers_health_facilities_write_perms = []
    registers_locations_query_perms = []
    registers_locations_write_perms = []
    registers_items_query_perms = []
    registers_items_write_perms = []
    registers_services_query_perms = []
    registers_services_write_perms = []

    extracts_master_data_perms = []
    extracts_officer_feedbacks_perms = []
    extracts_officer_renewals_perms = []
    extracts_phone_extract_perms = []
    extracts_upload_claims_perms = []

    master_data_password = None

    REGISTERS = ("diagnoses", "health_facilities", "locations", "items", "services")

    def __load_config(self, cfg):
        for field in cfg:
            if hasattr(ToolsConfig, field):
                setattr(ToolsConfig, field, cfg[field])
        # a configuration written before the query/write split only knows the
        # stacked key: keep honouring it for both directions
        stored = _overridden_keys(cfg)
        for register in self.REGISTERS:
            legacy = f"registers_{register}_perms"
            if legacy in stored:
                for kind in ("query", "write"):
                    if f"registers_{register}_{kind}_perms" not in stored:
                        setattr(ToolsConfig, f"registers_{register}_{kind}_perms", cfg[legacy])

    def ready(self):
        from core.models import ModuleConfiguration

        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CFG)
        self.__load_config(cfg)

    @classmethod
    def get_master_data_password(cls):
        return cls.master_data_password or (
            hasattr(settings, "MASTER_DATA_PASSWORD") and settings.MASTER_DATA_PASSWORD
        )
