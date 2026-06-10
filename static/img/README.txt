Category card images for the home page
======================================

Drop two image files here with these EXACT names:

  category-club.jpg      -> blue Chelsea kit (Клубные / Club category card)
  category-country.jpg   -> red Gambia kit  (Сборные / Country category card)

Accepted extensions: .jpg .jpeg .png .webp
(the code in apps/catalog/views.py:_curated_card_image checks these in order)

Recommended: landscape-ish crop, ~800x600 or larger, optimized < 300 KB.
If a file is missing, the card falls back to the newest product image in that
category, or a plain dark panel if there are none.

In production, run `python manage.py collectstatic` after adding the files.
