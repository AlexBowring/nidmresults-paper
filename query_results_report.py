"""
Display a paragraph describing the method used for group statistics based on
two NIDM-Results export: one from SPM, one from FSL.

@author: Camille Maumet <c.m.j.maumet@warwick.ac.uk>
@copyright: University of Warwick 2015
"""

import os
import re
import logging
import zipfile
from urllib2 import urlopen, URLError, HTTPError
import tempfile
from rdflib.graph import Graph, Namespace

# Examples of NIDM-Results archives
export_urls = [
    'https://docs.google.com/uc?id=0B5rWMFQteK5eMHVtVklCOHV6aGc&export=download'
    ]

# NIDM-Results 1.0.0 owl file
owl_file = "https://raw.githubusercontent.com/incf-nidash/nidm/master/nidm/\
nidm-results/terms/releases/nidm-results_110.owl"

OBO = Namespace("http://purl.obolibrary.org/obo/")
P_VALUE_FWER = OBO["OBI_0001265"]
Q_VALUE_FDR = OBO["OBI_0001442"]

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
tmpdir = tempfile.mkdtemp()


def threshold_txt(owl_graph, thresh_type, value, stat_type):
    # Namespaces and terms describing different thresholding approaches
    NIDM = Namespace("http://purl.org/nidash/nidm#")
    P_VALUE_UNC = NIDM["NIDM_0000160"]
    STATISTIC = OBO["STATO_0000039"]

    multiple_compa = ""
    is_p_value = True
    if thresh_type in [Q_VALUE_FDR, P_VALUE_FWER]:
        multiple_compa = "with correction for multiple \
comparisons "
        if thresh_type == Q_VALUE_FDR:
            thresh = "Q <= "
        else:
            thresh = "P <= "
    elif thresh_type == P_VALUE_UNC:
        thresh = "P <= "
    elif thresh_type == STATISTIC:
        is_p_value = False
        stat_abv = owl_graph.label(stat_type).replace("-statistic", "")
        thresh = stat_abv + " >= "

    thresh += "%0.2f" % float(value)

    if is_p_value:
        thresh += " (%s)" % (owl_graph.label(
            thresh_type).replace(" p-value", ""))

    return list([thresh, multiple_compa])

for url in export_urls:
    # Copy .nidm.zip export locally in a temp directory
    try:
        f = urlopen(url)
        data_id = re.search('id=(\w+)', url).groups()[0]
        tmpzip = os.path.join(tmpdir, data_id + ".nidm.zip")

        logger.info("downloading " + url + " at " + tmpzip)
        with open(tmpzip, "wb") as local_file:
            local_file.write(f.read())

    except HTTPError, e:
        print "HTTP Error:", e.code, url
    except URLError, e:
        print "URL Error:", e.reason, url

    # Unzip NIDM-Results export
    nidm_dir = os.path.join(tmpdir, data_id)
    with zipfile.ZipFile(tmpzip, 'r') as zf:
        zf.extractall(nidm_dir)

    nidm_doc = os.path.join(nidm_dir, "nidm.ttl")
    nidm_graph = Graph()
    nidm_graph.parse(nidm_doc, format='turtle')

    # Retreive the information of interest for the report by querying the
    # NIDM-Results export
    query = """
    prefix prov: <http://www.w3.org/ns/prov#>
    prefix nidm: <http://purl.org/nidash/nidm#>

    prefix ModelParamEstimation: <http://purl.org/nidash/nidm#NIDM_0000056>
    prefix withEstimationMethod: <http://purl.org/nidash/nidm#NIDM_0000134>
    prefix errorVarianceHomogeneous: <http://purl.org/nidash/nidm#NIDM_0000094>
    prefix SearchSpaceMaskMap: <http://purl.org/nidash/nidm#NIDM_0000068>
    prefix contrastName: <http://purl.org/nidash/nidm#NIDM_0000085>
    prefix statisticType: <http://purl.org/nidash/nidm#NIDM_0000123>
    prefix StatisticMap: <http://purl.org/nidash/nidm#NIDM_0000076>
    prefix searchVolumeInVoxels: <http://purl.org/nidash/nidm#NIDM_0000121>
    prefix searchVolumeInUnits: <http://purl.org/nidash/nidm#NIDM_0000136>
    prefix HeightThreshold: <http://purl.org/nidash/nidm#NIDM_0000034>
    prefix userSpecifiedThresholdType: <http://purl.org/nidash/\
nidm#NIDM_0000125>
    prefix ExtentThreshold: <http://purl.org/nidash/nidm#NIDM_0000026>
    prefix ExcursionSetMap: <http://purl.org/nidash/nidm#NIDM_0000025>
    prefix softwareVersion: <http://purl.org/nidash/nidm#NIDM_0000122>
    prefix clusterSizeInVoxels: <http://purl.org/nidash/nidm#NIDM_0000084>

    SELECT DISTINCT ?est_method ?homoscedasticity ?contrast_name ?stat_type
            ?search_vol_vox ?search_vol_units
            ?extent_thresh_value ?height_thresh_value
            ?extent_thresh_type ?height_thresh_type
            ?software ?excursion_set_id ?soft_version
        WHERE {
        ?mpe a ModelParamEstimation: .
        ?mpe withEstimationMethod: ?est_method .
        ?mpe prov:used ?error_model .
        ?error_model errorVarianceHomogeneous: ?homoscedasticity .
        ?stat_map prov:wasGeneratedBy/prov:used/prov:wasGeneratedBy ?mpe ;
                  a StatisticMap: ;
                  statisticType: ?stat_type ;
                  contrastName: ?contrast_name .
        ?search_region prov:wasGeneratedBy ?inference ;
                       a SearchSpaceMaskMap: ;
                       searchVolumeInVoxels: ?search_vol_vox ;
                       searchVolumeInUnits: ?search_vol_units .
        ?extent_thresh a ExtentThreshold: ;
                       a ?extent_thresh_type .
        {
            ?extent_thresh prov:value ?extent_thresh_value
        } UNION {
            ?extent_thresh clusterSizeInVoxels: ?extent_thresh_value
        } .
        ?height_thresh a HeightThreshold: ;
                       a ?height_thresh_type ;
                       prov:value ?height_thresh_value .
        ?inference prov:used ?stat_map ;
                   prov:used ?extent_thresh ;
                   prov:used ?height_thresh ;
                   prov:wasAssociatedWith ?soft_id .
        ?soft_id a ?software ;
                   softwareVersion: ?soft_version .
        ?excursion_set_id a ExcursionSetMap: ;
                   prov:wasGeneratedBy ?inference .

        FILTER(?software NOT IN (prov:SoftwareAgent, prov:Agent))
        FILTER(?height_thresh_type NOT IN (prov:Entity, HeightThreshold:))
        FILTER(?extent_thresh_type NOT IN (prov:Entity, ExtentThreshold:))

    }

    """
    sd = nidm_graph.query(query)

    owl_graph = Graph()
    owl_graph.parse(owl_file, format='turtle')

    if sd:
        for row in sd:
            est_method, homoscedasticity, contrast_name, stat_type, \
                search_vol_vox, search_vol_units, extent_value, \
                height_value, extent_thresh_type, height_thresh_type, \
                software, exc_set, soft_version = row

            # Convert all info to text
            thresh = ""
            multiple_compa = ""

            if extent_thresh_type in [Q_VALUE_FDR, P_VALUE_FWER]:
                inference_type = "Cluster-wise"
                thresh, multiple_compa = threshold_txt(
                    owl_graph, extent_thresh_type, extent_value, stat_type)
                clus_thresh, unused = threshold_txt(
                    owl_graph, height_thresh_type, height_value, stat_type)
                thresh += " with a cluster defining threshold " + clus_thresh

            else:
                inference_type = "Voxel-wise"
                thresh, multiple_compa = threshold_txt(
                    owl_graph, height_thresh_type, height_value, stat_type)
                thresh += " and clusters smaller than %d were discarded" \
                          % int(extent_value)

            if homoscedasticity:
                variance = 'equal'
            else:
                variance = 'unequal'

            print "-------------------"
            print "Group statistic was performed in %s (version %s). \
%s was performed assuming %s variances. %s inference \
was performed %susing a threshold %s. The search volume was %d cm^3 \
(%d voxels)." % (
                owl_graph.label(software), soft_version,
                owl_graph.label(est_method).capitalize(),
                variance, inference_type,
                multiple_compa, thresh, float(search_vol_units)/1000,
                int(search_vol_vox))
            print "-------------------"

    else:
        print "Query returned no results."
