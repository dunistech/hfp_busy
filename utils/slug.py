import re

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text

def generate_unique_slug(cur, base_slug):
    slug = base_slug
    counter = 1

    while True:
        cur.execute("SELECT 1 FROM businesses WHERE slug = %s", (slug,))
        if not cur.fetchone():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1
