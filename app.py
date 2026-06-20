"""PHIMA Streamlit application entry point.

Dental panoramic shorthand-to-report generator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class Finding:
    """Structured radiographic finding mapped from shorthand input."""

    interpretation: str
    diagnosis: str
    suggestion: str


ABBREVIATIONS: dict[str, Finding] = {
    "IM": Finding(
        "Tampak gambaran gigi impaksi/terpendam dengan posisi dan relasi terhadap struktur anatomis sekitar perlu dievaluasi secara klinis.",
        "Suspek impaksi gigi.",
        "Konsultasi bedah mulut untuk penilaian kebutuhan odontektomi dan pertimbangan pemeriksaan lanjutan bila diperlukan.",
    ),
    "H": Finding(
        "Tampak kehilangan sebagian struktur mahkota gigi yang mengarah pada karies/defek jaringan keras gigi.",
        "Suspek karies/kerusakan jaringan keras gigi.",
        "Evaluasi klinis, tes vitalitas bila diperlukan, serta perawatan restoratif sesuai kedalaman lesi.",
    ),
    "M": Finding(
        "Tampak kehilangan gigi pada regio terkait dengan gambaran ruang edentulus.",
        "Status edentulus parsial pada regio terkait.",
        "Pertimbangkan rehabilitasi prostodontik setelah evaluasi kondisi jaringan pendukung.",
    ),
    "D": Finding(
        "Tampak gambaran radiopak menyerupai restorasi/tumpatan pada mahkota gigi.",
        "Status pasca restorasi gigi.",
        "Evaluasi adaptasi tepi restorasi dan kontrol berkala secara klinis.",
    ),
    "V": Finding(
        "Tampak gambaran radiolusen periapikal/periodontal yang dapat berkaitan dengan proses patologis inflamasi.",
        "Suspek lesi periapikal atau periodontal.",
        "Korelasi dengan pemeriksaan klinis, tes vitalitas, dan pertimbangkan perawatan endodontik/periodontal.",
    ),
    "PE": Finding(
        "Tampak pelebaran ruang ligamen periodontal pada gigi terkait.",
        "Suspek perubahan periodontal/periapikal awal.",
        "Korelasi dengan gejala, tes perkusi, tes vitalitas, dan evaluasi oklusi.",
    ),
    "B": Finding(
        "Tampak kehilangan tinggi tulang alveolar yang mengarah pada resorpsi tulang pendukung periodontal.",
        "Suspek periodontitis dengan kehilangan tulang alveolar.",
        "Pemeriksaan periodontal komprehensif, scaling-root planing, dan kontrol faktor risiko.",
    ),
    "S": Finding(
        "Tampak kalkulus/radiopak servikal pada permukaan gigi terkait.",
        "Suspek deposit kalkulus.",
        "Disarankan scaling dan instruksi kebersihan rongga mulut.",
    ),
    "PR": Finding(
        "Tampak sisa akar gigi dengan kehilangan struktur mahkota yang bermakna.",
        "Suspek persistensi radiks/sisa akar.",
        "Evaluasi kelayakan perawatan konservatif; pertimbangkan ekstraksi bila prognosis buruk.",
    ),
    "PIR": Finding(
        "Tampak gambaran radiolusen interradikular/furkasi pada gigi berakar jamak.",
        "Suspek keterlibatan furkasi atau lesi interradikular.",
        "Pemeriksaan periodontal dan endodontik untuk menentukan sumber lesi.",
    ),
    "NP": Finding(
        "Tampak benih/gigi permanen belum erupsi pada regio terkait sesuai fase perkembangan dentisi.",
        "Status gigi permanen belum erupsi.",
        "Observasi pertumbuhan dan erupsi; evaluasi ortodontik bila terdapat hambatan erupsi.",
    ),
    "AP": Finding(
        "Tampak area radiolusen apikal pada gigi terkait.",
        "Suspek periodontitis apikal/lesi periapikal.",
        "Tes vitalitas dan pertimbangkan perawatan endodontik atau kontrol pascaperawatan.",
    ),
    "GR": Finding(
        "Tampak gambaran radiopak menyerupai restorasi mahkota/mahkota tiruan pada gigi terkait.",
        "Status gigi dengan restorasi indirek/mahkota tiruan.",
        "Evaluasi klinis terhadap adaptasi tepi, oklusi, dan jaringan periodontal sekitar.",
    ),
    "ED": Finding(
        "Tampak area edentulus pada regio terkait.",
        "Status edentulus pada regio terkait.",
        "Pertimbangkan perencanaan prostodontik atau implantologi sesuai indikasi.",
    ),
    "PG": Finding(
        "Tampak gambaran penyakit periodontal generalisata dengan penurunan tulang alveolar pada beberapa regio.",
        "Suspek periodontitis generalisata.",
        "Pemeriksaan periodontal menyeluruh dan terapi periodontal bertahap.",
    ),
    "TD": Finding(
        "Tampak benih/gigi dengan arah erupsi atau posisi yang menyimpang dari lengkung gigi.",
        "Suspek malposisi/ektopia gigi.",
        "Konsultasi ortodontik untuk evaluasi ruang dan arah erupsi.",
    ),
    "TP": Finding(
        "Tampak gigi tidak berada pada posisi fisiologis dalam lengkung rahang.",
        "Suspek translokasi/malposisi gigi.",
        "Evaluasi ortodontik dan korelasi dengan pemeriksaan intraoral.",
    ),
    "CROWDING": Finding(
        "Tampak ketidakteraturan posisi gigi dengan indikasi kekurangan ruang pada lengkung rahang.",
        "Suspek crowding dental.",
        "Konsultasi ortodontik untuk analisis ruang dan rencana perawatan.",
    ),
}

TOKEN_RE = re.compile(r"\b(CROWDING|PE|PR|PIR|NP|AP|GR|ED|PG|TD|TP|IM|H|M|D|V|B|S)\b", re.IGNORECASE)
TOOTH_RE = re.compile(r"\b(?:[1-4][1-8]|[5-8][1-5])\b")


def format_location(text: str) -> str:
    """Return a concise tooth/regio label from a shorthand fragment."""

    teeth = TOOTH_RE.findall(text)
    if teeth:
        unique_teeth = list(dict.fromkeys(teeth))
        return "gigi " + ", ".join(unique_teeth)
    return "regio yang dituliskan"


def parse_shorthand(shorthand: str) -> list[tuple[str, str, Finding]]:
    """Parse free-text shorthand into reportable findings."""

    entries: list[tuple[str, str, Finding]] = []
    for raw_line in shorthand.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        location = format_location(line)
        for match in TOKEN_RE.finditer(line):
            code = match.group(1).upper()
            entries.append((code, location, ABBREVIATIONS[code]))

    if not entries:
        normalized = shorthand.strip()
        for match in TOKEN_RE.finditer(normalized):
            code = match.group(1).upper()
            entries.append((code, format_location(normalized), ABBREVIATIONS[code]))
    return entries


def render_report(entries: list[tuple[str, str, Finding]]) -> dict[str, list[str]]:
    """Build Indonesian radiology report sections from parsed findings."""

    if not entries:
        return {
            "interpretasi": [
                "Belum ditemukan singkatan yang dapat dikenali. Masukkan shorthand seperti `18 IM`, `36 AP`, atau `PG Crowding`."
            ],
            "diagnosis": ["Belum dapat disusun karena data shorthand belum dikenali."],
            "saran": ["Periksa kembali format input dan gunakan daftar singkatan yang tersedia."],
        }

    interpretation: list[str] = []
    diagnosis: list[str] = []
    suggestions: list[str] = []
    seen_suggestions: set[str] = set()

    for code, location, finding in entries:
        interpretation.append(f"Pada {location}: {finding.interpretation} ({code})")
        diagnosis.append(f"{finding.diagnosis} Lokasi: {location}.")
        if finding.suggestion not in seen_suggestions:
            suggestions.append(finding.suggestion)
            seen_suggestions.add(finding.suggestion)

    return {"interpretasi": interpretation, "diagnosis": diagnosis, "saran": suggestions}


st.set_page_config(page_title="PHIMA Dental Report Generator", page_icon="🦷", layout="wide")

st.title("PHIMA")
st.caption("Generator laporan radiografi panoramik berbasis shorthand untuk kedokteran gigi.")

with st.sidebar:
    st.header("Daftar Singkatan")
    st.write(", ".join(ABBREVIATIONS.keys()))
    st.divider()
    st.markdown(
        """
        **Contoh input**
        ```text
        18 IM
        36 AP PE
        46 H
        PG Crowding
        ```
        """
    )

st.markdown(
    """
    Masukkan catatan shorthand radiografi panoramik. Aplikasi akan menyusun draf
    laporan dengan bahasa radiologi kedokteran gigi yang formal dan siap ditinjau.
    """
)

sample = "18 IM\n36 AP PE\n46 H\nPG Crowding"
shorthand = st.text_area(
    "Shorthand input",
    value=sample,
    height=180,
    placeholder="Contoh: 18 IM\n36 AP PE\n46 H\nPG Crowding",
)

generate = st.button("Generate Report", type="primary", use_container_width=True)

if generate:
    report = render_report(parse_shorthand(shorthand))

    st.subheader("Interpretasi Radiografis")
    for item in report["interpretasi"]:
        st.markdown(f"- {item}")

    st.subheader("Suspek Radiodiagnosis")
    for item in report["diagnosis"]:
        st.markdown(f"- {item}")

    st.subheader("Saran")
    for item in report["saran"]:
        st.markdown(f"- {item}")

    st.subheader("Disclaimer")
    st.info(
        "Laporan ini merupakan draf berbasis shorthand dan tidak menggantikan interpretasi final dokter gigi/radiolog kedokteran gigi. "
        "Temuan harus dikorelasikan dengan pemeriksaan klinis, riwayat pasien, kualitas citra, serta pemeriksaan penunjang lain bila diperlukan."
    )
else:
    st.info("Klik **Generate Report** untuk membuat draf laporan radiografi panoramik.")
