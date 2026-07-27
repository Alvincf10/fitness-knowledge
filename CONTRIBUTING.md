# Contributing

## Scope

Contributions must improve evidence quality, clarity, or coverage of the fitness knowledge base.

## Required Process

1. Use the matching template in `templates/`.
2. Include complete YAML frontmatter.
3. Assign an evidence grade (`A`–`D`).
4. Cite sources in simple APA format.
5. Add Related Articles links to connected topics.
6. Update the relevant file in `metadata/`.
7. Record the change in `CHANGELOG.md`.

## Allowed Sources (priority order)

1. Meta-analyses
2. Systematic reviews
3. ACSM position stands / guidelines
4. ISSN position stands
5. NSCA essentials / guidelines
6. Peer-reviewed journals

## Disallowed

- Bro science claims
- Clickbait framing
- Medical diagnosis or treatment advice
- Citations from fitness blogs or unverified social content
- Personal opinion presented as fact
- Placeholder text in finished articles

## Article Checklist

- [ ] Follows category template exactly
- [ ] YAML metadata present and valid
- [ ] Evidence grade assigned
- [ ] Scientific references included
- [ ] Related Articles cross-links present
- [ ] Metadata JSON updated
- [ ] Language is English, concise, evidence-first

## File Naming

Use kebab-case Markdown filenames, for example:

- `barbell-bench-press.md`
- `progressive-overload.md`
- `how-much-protein.md`

## IDs

Use stable IDs in frontmatter:

- Exercises: `exercise_<slug_with_underscores>`
- Science: `science_<slug_with_underscores>`
- Supplements: `supplement_<slug_with_underscores>`
- Nutrition: `nutrition_<slug_with_underscores>`
- FAQ: `faq_<slug_with_underscores>`
