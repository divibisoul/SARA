from sara.infra.nervo_vago import NervoVago, VagusBus
from sara.infra.vagus_bus import VagusNerveBus


def test_nervo_vago_is_the_single_vagus_implementation():
    assert NervoVago is VagusNerveBus
    assert VagusBus is NervoVago
