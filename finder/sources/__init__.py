"""One file per website. Each source turns a profile into listings.

To add a new site: copy autoscout24.py, change the URL building and the
parsing, then register it in SOURCES below.
"""

from finder.sources.autoscout24 import AutoScout24
from finder.sources.mobile_de import MobileDe

SOURCES = {
    AutoScout24.name: AutoScout24,
    MobileDe.name: MobileDe,
}
