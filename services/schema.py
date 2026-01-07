from flask import url_for

def business_schema(business):
    return {
        "@context": "https://schema.org",
        "@type": business.get("schema_type", "LocalBusiness"),
        "@id": url_for(
            "business.public_business_profile",
            business_slug=business["slug"],
            _external=True
        ) + "#business",
        "name": business["business_name"],
        "url": url_for(
            "business.public_business_profile",
            business_slug=business["slug"],
            _external=True
        ),
        "image": business.get("media_url"),
        "description": (business.get("description") or "")[:300],
        "telephone": business.get("phone_number"),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": business.get("address"),
            "addressLocality": "Ajah",
            "addressRegion": "Lagos",
            "addressCountry": "NG",
        },
    }


def category_schema(category, businesses):
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": url_for(
            "categories.businesses_by_category",
            category_slug=category["slug"],
            _external=True
        ) + "#collection",
        "name": f'{category["category_name"]} in Ajah',
        "url": url_for(
            "categories.businesses_by_category",
            category_slug=category["slug"],
            _external=True
        ),
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(businesses),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": idx + 1,
                    "url": url_for(
                        "business.public_business_profile",
                        business_slug=biz["slug"],
                        _external=True
                    ),
                }
                for idx, biz in enumerate(businesses)
            ],
        },
    }
