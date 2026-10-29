# -*- coding: utf-8 -*-
"""Testy modułu services: GetCapabilities, dobór warstw, adresy, Overpass."""
import pytest

from gis_assistant_ai import services as svc

WMS_CAPS = (
    b'<?xml version="1.0"?>\n'
    b'<WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms">\n'
    b' <Service><Title>GDOS - formy ochrony przyrody</Title></Service>\n'
    b' <Capability>\n'
    b'  <Request><GetMap><Format>image/jpeg</Format>'
    b'<Format>image/png</Format></GetMap></Request>\n'
    b'  <Layer><Title>root</Title><CRS>EPSG:2180</CRS><CRS>EPSG:4326</CRS>\n'
    b'   <EX_GeographicBoundingBox>'
    b'<westBoundLongitude>14.1</westBoundLongitude>'
    b'<eastBoundLongitude>24.2</eastBoundLongitude>\n'
    b'    <southBoundLatitude>49.0</southBoundLatitude>'
    b'<northBoundLatitude>54.9</northBoundLatitude>'
    b'</EX_GeographicBoundingBox>\n'
    b'   <Layer><Name>ParkiNarodowe</Name><Title>Parki narodowe</Title>'
    b'</Layer>\n'
    b'   <Layer><Name>Rezerwaty</Name><Title>Rezerwaty przyrody</Title>'
    b'<CRS>EPSG:3857</CRS></Layer>\n'
    b'   <Layer><Name>ParkiKrajobrazowe</Name>'
    b'<Title>Parki krajobrazowe w Polsce</Title></Layer>\n'
    b'  </Layer>\n'
    b' </Capability>\n'
    b'</WMS_Capabilities>')

WMTS_CAPS = (
    b'<?xml version="1.0"?>\n'
    b'<Capabilities xmlns="http://www.opengis.net/wmts/1.0" '
    b'xmlns:ows="http://www.opengis.net/ows/1.1" version="1.0.0">\n'
    b' <ows:ServiceIdentification><ows:Title>Ortofotomapa</ows:Title>'
    b'</ows:ServiceIdentification>\n'
    b' <Contents>\n'
    b'  <Layer><ows:Title>Ortofotomapa</ows:Title>'
    b'<ows:Identifier>ORTOFOTOMAPA</ows:Identifier>\n'
    b'   <ows:WGS84BoundingBox><ows:LowerCorner>14 49</ows:LowerCorner>\n'
    b'    <ows:UpperCorner>24.5 55</ows:UpperCorner></ows:WGS84BoundingBox>\n'
    b'   <Style isDefault="true"><ows:Identifier>default</ows:Identifier>'
    b'</Style>\n'
    b'   <Format>image/jpeg</Format>\n'
    b'   <TileMatrixSetLink><TileMatrixSet>EPSG:2180</TileMatrixSet>'
    b'</TileMatrixSetLink>\n'
    b'   <TileMatrixSetLink>'
    b'<TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>'
    b'</TileMatrixSetLink>\n'
    b'  </Layer>\n'
    b'  <TileMatrixSet><ows:Identifier>EPSG:2180</ows:Identifier>'
    b'<ows:SupportedCRS>urn:ogc:def:crs:EPSG::2180</ows:SupportedCRS>'
    b'</TileMatrixSet>\n'
    b'  <TileMatrixSet><ows:Identifier>GoogleMapsCompatible</ows:Identifier>'
    b'<ows:SupportedCRS>urn:ogc:def:crs:EPSG::3857</ows:SupportedCRS>'
    b'</TileMatrixSet>\n'
    b' </Contents>\n'
    b'</Capabilities>')

WFS_CAPS = (
    '<?xml version="1.0"?>\n'
    '<wfs:WFS_Capabilities version="2.0.0" '
    'xmlns:wfs="http://www.opengis.net/wfs/2.0" '
    'xmlns:ows="http://www.opengis.net/ows/1.1">\n'
    ' <ows:ServiceIdentification><ows:Title>PRG</ows:Title>'
    '</ows:ServiceIdentification>\n'
    ' <wfs:FeatureTypeList>\n'
    '  <wfs:FeatureType><wfs:Name>ms:A03_Granice_gmin</wfs:Name>'
    '<wfs:Title>Granice gmin</wfs:Title>\n'
    '   <wfs:DefaultCRS>urn:ogc:def:crs:EPSG::2180</wfs:DefaultCRS>'
    '<wfs:OtherCRS>urn:ogc:def:crs:EPSG::4326</wfs:OtherCRS>\n'
    '  </wfs:FeatureType>\n'
    '  <wfs:FeatureType><wfs:Name>ms:A02_Granice_powiatow</wfs:Name>'
    '<wfs:Title>Granice powiatów</wfs:Title></wfs:FeatureType>\n'
    ' </wfs:FeatureTypeList>\n'
    '</wfs:WFS_Capabilities>').encode("utf-8")


class TestCapabilities:
    """Odczyt GetCapabilities WMS, WMTS i WFS."""

    def test_wms(self):
        info = svc.parse_capabilities(
            "wms", WMS_CAPS,
            "https://sdi.gdos.gov.pl/wms?SERVICE=WMS&REQUEST=GetCapabilities")
        assert info["title"] == "GDOS - formy ochrony przyrody"
        assert info["url"] == "https://sdi.gdos.gov.pl/wms"
        assert [ly["name"] for ly in info["layers"]] == [
            "ParkiNarodowe", "Rezerwaty", "ParkiKrajobrazowe"]
        # dziedziczenie układów
        assert info["layers"][1]["crs"] == ["EPSG:2180", "EPSG:3857",
                                            "EPSG:4326"]
        # dziedziczenie zasięgu
        assert info["layers"][0]["bbox"] == [14.1, 49.0, 24.2, 54.9]
        assert svc.pick_format(info["formats"]) == "image/png"

    def test_wmts(self):
        info = svc.parse_capabilities("wmts", WMTS_CAPS,
                                      "https://mapy.geoportal.gov.pl/wmts")
        ly = info["layers"][0]
        assert (ly["style"] == "default"
                and ly["bbox"] == [14.0, 49.0, 24.5, 55.0])
        assert svc.pick_matrix_set(ly["matrix_sets"], ["EPSG:3857"])[
            "id"] == "GoogleMapsCompatible"
        assert svc.pick_matrix_set(ly["matrix_sets"])["id"] == "EPSG:2180"

    def test_wfs(self):
        info = svc.parse_capabilities(
            "wfs", WFS_CAPS,
            "https://mapy.geoportal.gov.pl/wss/service/PZGIK/PRG/WFS")
        assert info["layers"][0]["crs"] == ["EPSG:2180", "EPSG:4326"]
        assert svc.match_layers(info["layers"], ["granice gmin"])[0][
            "name"] == "ms:A03_Granice_gmin"
        assert svc.match_layers(info["layers"], "granice powiatow")[0][
            "name"] == "ms:A02_Granice_powiatow"

    def test_exception_report(self):
        raw = (b"<ServiceExceptionReport><ServiceException>Brak warstwy"
               b"</ServiceException></ServiceExceptionReport>")
        with pytest.raises(svc.ServiceError, match="Brak warstwy"):
            svc.parse_capabilities("wms", raw, "https://example.com/wms")

    def test_not_xml(self):
        with pytest.raises(svc.ServiceError):
            svc.parse_capabilities("wms", b"<html><body>404",
                                   "https://example.com/wms")


class TestMatchLayers:
    """Dobór warstw usługi po nazwie technicznej albo słowach z tytułu."""

    layers = [{"name": "ParkiNarodowe", "title": "Parki narodowe"},
              {"name": "ParkiKrajobrazowe",
               "title": "Parki krajobrazowe w Polsce"},
              {"name": "Rezerwaty", "title": "Rezerwaty przyrody"}]

    def test_exact_technical_name(self):
        assert svc.match_layers(self.layers,
                                "Rezerwaty")[0]["name"] == "Rezerwaty"

    def test_title_words_without_polish_letters(self):
        assert svc.match_layers(self.layers, ["parki narodowe"])[0][
            "name"] == "ParkiNarodowe"
        assert svc.match_layers(self.layers, ["Parki KRAJOBRAZOWE"])[0][
            "name"] == "ParkiKrajobrazowe"

    def test_several_and_none(self):
        assert len(svc.match_layers(self.layers,
                                    ["parki narodowe", "rezerwaty"])) == 2
        assert svc.match_layers(self.layers, ["lotniska"]) == []
        # bez wskazania i kilka warstw – nie zgadujemy
        assert svc.match_layers(self.layers, []) == []

    def test_each_layer_picked_once(self):
        picked = svc.match_layers(self.layers,
                                  ["ParkiNarodowe", "parki narodowe",
                                   "rezerwaty"])
        assert [ly["name"] for ly in picked] == ["ParkiNarodowe", "Rezerwaty"]


class TestUrls:
    """Adresy usług, adresy w sieci wewnętrznej i dane spod adresu."""

    def test_base_url_keeps_other_params(self):
        assert svc.base_url("https://x.pl/cgi?map=a.map&SERVICE=WMS"
                            "&request=GetCapabilities") == (
            "https://x.pl/cgi?map=a.map")

    def test_capabilities_url(self):
        assert svc.capabilities_url("wmts", "https://x.pl/wmts") == (
            "https://x.pl/wmts?SERVICE=WMTS&REQUEST=GetCapabilities")
        with pytest.raises(svc.ServiceError):
            svc.capabilities_url("wms", "file:///C:/dane.xml")

    @pytest.mark.parametrize("url", [
        "http://localhost:8080/wfs", "http://127.0.0.1/x",
        "http://10.1.2.3/wms", "http://192.168.0.5/a.geojson",
        "http://[::1]/x", "http://serwer.local/wms", "file:///etc/passwd"])
    def test_private(self, url):
        assert svc.is_private_url(url)

    def test_public_ip(self):
        assert not svc.is_private_url("https://8.8.8.8/wms")

    def test_remote_source(self):
        assert svc.remote_source(
            "/vsicurl/https://x.pl/a.geojson|layername=a") == (
            "https://x.pl/a.geojson", {"layername": "a"})
        assert svc.remote_source("C:/dane/a.gpkg") is None


class TestOverpass:
    """Zapytania Overpass: format czytelny dla GDAL, serwery zapasowe."""

    def test_readable(self):
        url = ("https://overpass-api.de/api/interpreter?data="
               + "%5Bout%3Ajson%5D%3Bway%5Bbuilding%5D%3Bout+geom%3B")
        out = svc.overpass_readable(url)
        assert ("out%3Axml" in out
                and "out+body%3B%3E%3Bout+skel+qt%3B" in out)

    def test_other_urls_untouched(self):
        assert svc.overpass_readable("https://x.pl/a.geojson") == (
            "https://x.pl/a.geojson")

    def test_mirrors(self):
        urls = svc.overpass_mirror_urls(
            "https://overpass-api.de/api/interpreter?data=abc")
        assert (urls and urls[0].endswith("/api/interpreter?data=abc")
                and "overpass-api.de" not in urls[0])
        assert svc.overpass_mirror_urls(
            "https://x.pl/api/interpreter?data=abc") == []

    def test_error_detection(self):
        assert svc.overpass_error(b'<osm><remark> runtime error: Query timed '
                                  b'out </remark></osm>')
        assert not svc.overpass_error(b'<osm version="0.6"><node '
                                      b'id="1"/></osm>')


@pytest.mark.parametrize("head,ctype,url,ext", [
    (b"PK\x03\x04", "", "https://x.pl/d", ".zip"),
    (b'{"type":"FeatureCollection"}', "", "https://x.pl/d", ".geojson"),
    (b'<?xml version="1.0"?><osm version="0.6">', "",
     "https://overpass-api.de/api/interpreter", ".osm"),
    (b'<kml xmlns="http://www.opengis.net/kml/2.2">', "", "https://x.pl/d",
     ".kml"),
    (b'<?xml version="1.0"?><wfs:FeatureCollection>', "text/xml",
     "https://x.pl/d", ".gml"),
    (b"SQLite format 3\x00", "", "https://x.pl/d", ".gpkg"),
    (b"<!DOCTYPE html><html>", "text/html", "https://x.pl/d.geojson", None),
])
def test_sniff_ext(head, ctype, url, ext):
    assert svc.sniff_ext(head, ctype, url) == ext


def test_epsg():
    assert svc.epsg("urn:ogc:def:crs:EPSG::2180") == "EPSG:2180"
    assert svc.epsg(
        "http://www.opengis.net/def/crs/EPSG/0/4326") == "EPSG:4326"
    assert svc.pick_crs(["EPSG:4326", "EPSG:2180"],
                        ["EPSG:2177"]) == "EPSG:2180"
    assert svc.pick_crs(["EPSG:4326", "EPSG:2177"],
                        ["EPSG:2177"]) == "EPSG:2177"


class TestOverpassServers:
    """Przeciążenie Overpass i wybór kolejnego serwera."""

    gateway = ("QuickOSM.core.exceptions.NetWorkErrorException: ('Overpass "
               "API : Pobieranie nie powiodło się: Error transferring "
               "https://overpass-api.de/api/interpreter?info="
               "QgisQuickOSMPlugin - server replied: Gateway Timeout', None)")

    def test_transient(self):
        assert svc.overpass_transient(self.gateway)
        assert svc.overpass_transient("OverpassManyRequestException")
        bad = ("QuickOSM.core.exceptions.OverpassBadRequestException: "
               "('Błędne żądanie', None)")
        assert not svc.overpass_transient(bad)
        assert not svc.overpass_transient("OverpassMemoryException")

    def test_server_in_error(self):
        assert svc.overpass_server_in_error(self.gateway) == (
            "https://overpass-api.de/api/interpreter")

    def test_next_server(self):
        assert svc.next_overpass_server(
            ["https://overpass-api.de/api/interpreter"]) == (
            "https://overpass.private.coffee/api/interpreter")
        tried = list(svc.OVERPASS_SERVERS)
        assert svc.next_overpass_server(tried) is None
        fr = "https://overpass.openstreetmap.fr/api/interpreter"
        assert svc.next_overpass_server([fr]) == svc.OVERPASS_SERVERS[0]
        # lz4 to węzeł serwera głównego – kolejny jest serwer zapasowy
        assert svc.next_overpass_server(
            ["https://lz4.overpass-api.de/api/interpreter"]) == (
            svc.OVERPASS_SERVERS[1])

    def test_known(self):
        assert svc.known_overpass_server(
            "https://overpass-api.de/api/interpreter")
        assert not svc.known_overpass_server(
            "https://overpass.openstreetmap.fr/api/interpreter")


class TestPrivateUrls:
    """Ocena adresów bez DNS i adresy zaszyte w URI warstw."""

    def test_static_verdicts(self):
        assert svc.private_url_static("http://localhost:8080/x") is True
        assert svc.private_url_static("http://10.1.2.3/wms") is True
        assert svc.private_url_static("http://[fe80::1]/") is True
        assert svc.private_url_static("http://nas.local/") is True
        assert svc.private_url_static("http://8.8.8.8/") is False
        # nazwa – wymaga DNS
        assert svc.private_url_static("https://sdi.gdos.gov.pl/wms") is None
        assert svc.private_url_static("not a url") is True

    def test_uri_http_url(self):
        assert svc.uri_http_url(
            "url='https://mapy.geoportal.gov.pl/wss/PRG/WFS' "
            "typename='ms:A03' version='auto'") == (
            "https://mapy.geoportal.gov.pl/wss/PRG/WFS")
        assert svc.uri_http_url(
            "crs=EPSG:2180&format=image/png&layers=Raster&styles="
            "&url=http://192.168.1.5/wms") == "http://192.168.1.5/wms"
        assert svc.uri_http_url(
            "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            "&zmin=0") == "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        assert svc.uri_http_url("https://x/y.geojson|layername=a") == (
            "https://x/y.geojson")
        assert (svc.uri_http_url("/data/x.shp") is None
                and svc.uri_http_url("") is None)

    def test_redact_url(self):
        assert svc.redact_url("https://host/wms?key=SECRET&layers=a") == (
            "https://host/wms?key=***&layers=a")


class TestBdot10k:
    """Kody TERYT i klas BDOT10k, adresy paczek i pliki w paczce."""

    def test_powiat_code(self):
        assert svc.bdot10k_powiat_code("1418") == "1418"
        assert svc.bdot10k_powiat_code("141805_2") == "1418"
        assert svc.bdot10k_powiat_code("141805_2.0001.123/4") == "1418"
        assert svc.bdot10k_powiat_code("powiat piaseczyński (1418)") == "1418"
        assert svc.bdot10k_powiat_code("14") is None
        assert (svc.bdot10k_powiat_code("") is None
                and svc.bdot10k_powiat_code(None) is None)

    def test_class(self):
        assert svc.bdot10k_class("OT_SKDR_L") == "OT_SKDR_L"
        assert svc.bdot10k_class("skdr_l") == "OT_SKDR_L"
        assert svc.bdot10k_class("OT_BUBD_A (budynki)") == "OT_BUBD_A"
        assert svc.bdot10k_class("budynki") is None

    def test_package_urls(self):
        urls = svc.bdot10k_package_urls("1418")
        assert urls[0] == ("https://opendata.geoportal.gov.pl/bdot10k/"
                           "schemat2021/GPKG/14/1418_GPKG.zip")
        assert (urls[1].endswith("/SHP/14/1418_SHP.zip")
                and urls[2].endswith("/14/1418_GML.zip"))

    def test_members(self):
        names = ["1418/PL.PZGiK.339.1418__OT_SKDR_L.xml", "1418/OT_SKDR_L.shp",
                 "1418/OT_SKDR_L.dbf",
                 "1418/OT_SKDR_L.gpkg", "1418/BDOT10k_1418.gpkg",
                 "__MACOSX/._OT_SKDR_L.gpkg", "1418/readme.txt"]
        named, gpkgs = svc.bdot10k_members(names, "OT_SKDR_L")
        assert named == ["1418/OT_SKDR_L.gpkg", "1418/OT_SKDR_L.shp",
                         "1418/PL.PZGiK.339.1418__OT_SKDR_L.xml"]
        assert gpkgs == ["1418/BDOT10k_1418.gpkg"]
        assert svc.bdot10k_members(names, "OT_BUBD_A") == (
            [], ["1418/OT_SKDR_L.gpkg", "1418/BDOT10k_1418.gpkg"])


def test_xml_text_helper():
    root = svc.ET.fromstring("<a><b>  x </b><c/><d>   </d></a>")
    assert svc._text(root, "b") == "x"
    assert svc._text(root, "c", "-") == "-"
    assert svc._text(root, "d") == ""
    assert svc._text(root, "brak", "-") == "-"
    assert svc._text(None, "b", "-") == "-"
