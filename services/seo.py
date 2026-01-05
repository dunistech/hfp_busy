from flask import g, request, url_for

DEFAULTS = {
    "site_name": "Ajah Businenesses",
    "base_location": "Ajah, Lagos",
    "default_image": "/static/images/seo/default-og.png",
    "twitter_handle": "@ssalesnet",
}


def build_seo(
    *,
    title: str,
    description: str,
    image: str | None = None,
    schema: dict | None = None,
    canonical: str | None = None,
    noindex: bool = False,
):
    """
    Central SEO builder.
    Returns a dict passed directly to templates.
    """
    
    default_image = (
        getattr(g, "logo_path", None)
        or url_for("static", filename="img/icons/dunislogo_128.png", _external=True)
    )
    
    return {
        "title": title.strip(),
        "description": description.strip(),
        "image": image or default_image,
        "canonical": canonical or request.url,
        "schema": schema,
        "noindex": noindex,
        "site_name": DEFAULTS["site_name"],
        "twitter_handle": DEFAULTS["twitter_handle"],
    }
