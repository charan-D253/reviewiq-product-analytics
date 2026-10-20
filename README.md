# ReviewIQ — Product Review Analytics

A Flask web dashboard for the **Online Product Reviews and Rating Sentiment-Category Analysis System** college project.

## What is included

- `app.py` — Flask API, CSV validation/cleaning, computed analysis, and keyword-based review sentiment.
- `templates/index.html` — dashboard page.
- `static/style.css` — responsive dashboard styling.
- `static/app.js` — interactive dashboard UI and charts.
- `requirements.txt` — Python dependencies, including Gunicorn for Render.
- `Procfile`, `render.yaml`, `.python-version` — hosting configuration.
- `START_WEBSITE.bat` — Windows local startup helper.

There is **no sample dataset** included. The dashboard intentionally shows an empty state until you upload your actual Amazon CSV. This prevents fake product records and hardcoded analysis.

## Run locally on Windows (no VS Code required)

1. Install Python 3.13 (64-bit) from <https://www.python.org/downloads/windows/>.
2. Extract the project ZIP.
3. Open the extracted `ReviewIQ_Complete_Project` folder.
4. Double-click `START_WEBSITE.bat`.
5. Keep the black terminal window open and visit <http://127.0.0.1:8000> in your browser.
6. Open **Upload dataset** and select the actual CSV file.

The first run installs packages, so an internet connection is required. If Windows asks about network access, allow access on private networks.

## Publish to GitHub + Render from scratch

For the least confusing setup, create a **new public GitHub repository**. Do not upload this ZIP file as the only source file; Render needs the extracted source tree.

### Recommended upload method: GitHub Desktop (preserves folders)

1. Create a new public repository on <https://github.com/new>, for example `reviewiq-product-analytics-clean`. Leave “Add a README” unchecked.
2. Install/open GitHub Desktop: <https://desktop.github.com/> and sign in.
3. In GitHub Desktop, choose **File → Clone repository**, select the new repository, and clone it to your computer.
4. Open the extracted `ReviewIQ_Complete_Project` folder in File Explorer. Copy its *contents* (including `static` and `templates` folders) into the cloned repository folder. If Windows asks whether to replace a file, choose the project copy.
5. In GitHub Desktop, enter a summary such as `Add complete ReviewIQ project`, click **Commit to main**, then click **Push origin**.
6. In Render, create **New → Web Service → Public Git Repository**, enter the new public repository URL, and connect it.
7. Use these settings:

   - **Language:** Python 3
   - **Branch:** `main`
   - **Root Directory:** leave blank
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance:** Free (if offered for the account)

8. Remove any unused/blank Environment Variables row; this app does not require one for a same-origin deployment.
9. Click **Deploy Web Service** and wait for the deployment to finish. Render will show a public `https://...onrender.com` URL when the service is live.

### Important folder structure

The GitHub repository root must contain these items, not just a ZIP file and not a nested extra project folder:

```text
app.py
requirements.txt
Procfile
render.yaml
.python-version
static/
  app.js
  style.css
templates/
  index.html
```

The `static` and `templates` directories must be in the same root directory as `app.py`.

## Dataset columns required

The uploaded CSV must contain all 16 columns:

`product_id`, `product_name`, `category`, `discounted_price`, `actual_price`, `discount_percentage`, `rating`, `rating_count`, `about_product`, `user_id`, `user_name`, `review_id`, `review_title`, `review_content`, `img_link`, `product_link`.

The app cleans currency/percentage/number strings, validates required columns, and recalculates metrics from the uploaded data. It uses `img_link` and `product_link` when valid. Invalid images show placeholders.

## API endpoints

- `GET /health`
- `GET /products`
- `GET /products/<product_id>`
- `GET /dashboard-summary`
- `GET /rating-analysis`
- `GET /category-analysis`
- `GET /most-reviewed-products`
- `GET /review-analysis`
- `POST /analyze-review`
- `POST /analyze-dataset`

## Analysis notes

- Review sentiment uses a transparent keyword-lexicon heuristic. It is not a trained ML model and predictions can be wrong; the app does not invent a model confidence score.
- The source's overall product `rating` is not individual one- through five-star vote counts. The app does not fabricate those distributions.
- Packed review cells are only separated when safely recognizable as list-formatted values. Plain text is not split at commas because commas may be part of the review.
- Highest `rating_count` is labelled “Most Reviewed Products,” not “Best-Selling Products.” The dataset does not provide verified sales volume.
- On free hosting, uploaded files may not persist across service restarts; upload the CSV again if needed.
