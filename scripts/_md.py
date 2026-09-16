"""Small shared helpers for the Markdown converters: front matter, inline LaTeX."""
import re

FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)

GREEK = {r'\tau': 'τ', r'\theta': 'θ', r'\sigma': 'σ', r'\Phi': 'Φ', r'\Omega': 'Ω', r'\pi': 'π',
         r'\ell': 'ℓ', r'\epsilon': 'ε', r'\Delta': 'Δ', r'\gamma': 'γ', r'\mu': 'μ', r'\kappa': 'κ',
         r'\delta': 'δ', r'\varnothing': '∅', r'\in': '∈', r'\sim': '∼', r'\approx': '≈', r'\ge': '≥',
         r'\le': '≤', r'\times': '×', r'\mid': '|', r'\to': '→', r'\infty': '∞', r'\cdot': '·',
         r'\lambda': 'λ', r'\rho': 'ρ', r'\alpha': 'α', r'\beta': 'β', r'\phi': 'φ', r'\eta': 'η',
         r'\lfloor': '⌊', r'\rfloor': '⌋', r'\odot': '⊙', r'\gg': '≫', r'\ll': '≪', r'\propto': '∝',
         r'\ne': '≠', r'\dots': '…', r'\ldots': '…', r'\cdots': '⋯', r'\pm': '±', r'\partial': '∂',
         r'\psi': 'ψ', r'\varphi': 'φ', r'\omega': 'ω', r'\xi': 'ξ', r'\nu': 'ν', r'\zeta': 'ζ',
         r'\lVert': '‖', r'\rVert': '‖', r'\|': '‖'}


def split_front_matter(src: str):
    """Return (front_matter_dict, body). Only flat `key: value` and `key: [a, b]` lines are parsed."""
    m = FRONT.match(src)
    if not m:
        return {}, src
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            meta[k.strip()] = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        else:
            meta[k.strip()] = v.strip("\"'")
    return meta, src[m.end():]


def tex_inline_html(s: str) -> str:
    """Best-effort LaTeX -> HTML (unicode + sub/sup) for inline math in Confluence bodies."""
    s = s.replace(r'\,', '').replace(r'\;', ' ').replace(r'\!', '')
    s = re.sub(r'\\(?:l|c)?dots\b', '…', s)
    s = re.sub(r'\\mathcal\{L\}', '𝓛', s)
    s = re.sub(r'\\mathcal\{N\}', '𝒩', s)
    s = re.sub(r'\\mathcal\{D\}', '𝒟', s)
    s = re.sub(r'\\mathbb\{R\}', 'ℝ', s)
    s = re.sub(r'\\text\{([^}]*)\}', r'\1', s)
    for acc, mark in (("hat", "\u0302"), ("bar", "\u0304"), ("dot", "\u0307"), ("tilde", "\u0303")):
        s = re.sub(r'\\' + acc + r'\s*\\?([A-Za-z]+)', lambda m: GREEK.get('\\' + m.group(1), m.group(1)) + mark, s)
    s = re.sub(r'\\sqrt\{([^}]*)\}', r'√(\1)', s)
    s = re.sub(r'\\(min|max|log|exp|sg|KL)\b', r'\1', s)
    s = re.sub(r'\\math(?:rm|bf|sf)\{([^}]*)\}', r'\1', s)
    s = s.replace(r'\{', '{').replace(r'\}', '}')
    for k in sorted(GREEK, key=len, reverse=True):
        s = s.replace(k, GREEK[k])
    s = re.sub(r'_\{([^}]*)\}', r'<sub>\1</sub>', s)
    s = re.sub(r'\^\{([^}]*)\}', r'<sup>\1</sup>', s)
    s = re.sub(r'_(\w)', r'<sub>\1</sub>', s)
    s = re.sub(r'\^(\w)', r'<sup>\1</sup>', s)
    return '<em>' + s.replace('\\', '') + '</em>'


INLINE_MATH = re.compile(r'(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)')
IMAGE = re.compile(r'^!\[(.*?)\]\(([^)]+)\)\s*$')
