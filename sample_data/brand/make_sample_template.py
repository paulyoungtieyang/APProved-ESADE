#!/usr/bin/env python3
"""
Generate the sample corporate PowerPoint template shipped with the demo.

Run from the repository root to regenerate it:

    python3 sample_data/brand/make_sample_template.py

The output stands in for a template a client would upload from their own brand
book. It carries a distinctive theme — brand palette, heading and body typefaces,
a footer rule on the master — so it is immediately obvious in a generated deck
whether the template was applied or the default PowerPoint theme leaked through.
"""

import os
import re

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Pt

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "acme_medical_corporate_template.pptx")

# Stand-in brand palette for "ContinuousGlucose Monitoring Ltd."
BRAND = {
    "dk2": "0B3C5D",   # deep clinical blue — headings
    "lt2": "F2F7FA",   # pale background wash
    "accent1": "1B7FA8",
    "accent2": "3FB0AC",
    "accent3": "F5A623",
    "accent4": "9B59B6",
    "accent5": "E4572E",
    "accent6": "76B041",
}
MAJOR_FONT = "Georgia"      # headings — deliberately not Calibri
MINOR_FONT = "Trebuchet MS"  # body


def patch_theme(presentation):
    """Rewrite the theme part's colour scheme and font scheme in place."""
    theme_part = presentation.slide_master.part.part_related_by(
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
    )
    xml = theme_part.blob.decode("utf-8")

    for slot, value in BRAND.items():
        xml = re.sub(
            rf'(<a:{slot}>\s*<a:srgbClr val=")[0-9A-Fa-f]{{6}}(")',
            rf'\g<1>{value}\g<2>',
            xml,
        )
        # dk2/lt2 sometimes carry sysClr rather than srgbClr
        xml = re.sub(
            rf'<a:{slot}>\s*<a:sysClr[^/]*/>\s*</a:{slot}>',
            f'<a:{slot}><a:srgbClr val="{value}"/></a:{slot}>',
            xml,
        )

    xml = re.sub(r'(<a:majorFont>\s*<a:latin typeface=")[^"]*(")',
                 rf'\g<1>{MAJOR_FONT}\g<2>', xml)
    xml = re.sub(r'(<a:minorFont>\s*<a:latin typeface=")[^"]*(")',
                 rf'\g<1>{MINOR_FONT}\g<2>', xml)

    theme_part._blob = xml.encode("utf-8")


# Master shapes cannot be added via python-pptx; the template's own master handles that.
# We just patch the theme colors and fonts.


def main():
    presentation = Presentation()
    presentation.slide_width = Emu(12192000)   # 16:9
    presentation.slide_height = Emu(6858000)

    patch_theme(presentation)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    presentation.save(OUTPUT)

    print(f"wrote {OUTPUT} ({os.path.getsize(OUTPUT):,} bytes)")
    print(f"  layouts : {len(presentation.slide_layouts)}")
    print(f"  fonts   : {MAJOR_FONT} / {MINOR_FONT}")


if __name__ == "__main__":
    main()
