"""Curated, user-facing role options for role-based interview practice."""

from django.utils.text import slugify


ROLE_OPTIONS = (
    ('frontend-developer', 'Frontend Developer'),
    ('backend-developer', 'Backend Developer'),
    ('full-stack-developer', 'Full-Stack Developer'),
    ('mobile-developer', 'Mobile Developer'),
    ('data-analyst', 'Data Analyst'),
    ('data-scientist', 'Data Scientist'),
    ('machine-learning-engineer', 'Machine Learning Engineer'),
    ('devops-engineer', 'DevOps Engineer'),
    ('qa-automation-engineer', 'QA Automation Engineer'),
    ('product-manager', 'Product Manager'),
    ('ui-ux-designer', 'UI/UX Designer'),
    ('hr-specialist', 'HR Specialist'),
)

EXPERIENCE_LEVELS = (
    ('fresher', 'Fresher / Entry level'),
    ('1-2-years', '1–2 years'),
    ('3-5-years', '3–5 years'),
    ('5-plus-years', '5+ years'),
)

FOCUS_AREAS = (
    ('mixed', 'Mixed interview'),
    ('technical', 'Technical skills'),
    ('behavioral', 'Behavioural and communication'),
    ('system-design', 'System design and architecture'),
)


def label_for(options, value):
    """Return the displayed label for a controlled option, or None."""
    return dict(options).get(value)


def normalize_custom_role(value):
    """Normalize a user-entered role before it is included in an AI prompt."""
    normalized = ' '.join(value.split())
    if not 2 <= len(normalized) <= 100:
        return None, None
    return normalized, f'custom-{slugify(normalized)[:50]}'
