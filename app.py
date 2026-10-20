from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import os, ast, re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'amazon_products.csv')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
CORS(app)

REQUIRED = ['product_id','product_name','category','discounted_price','actual_price','discount_percentage','rating','rating_count','about_product','user_id','user_name','review_id','review_title','review_content','img_link','product_link']
DF = pd.DataFrame(columns=REQUIRED)
DATA_SOURCE = 'No dataset loaded'

POSITIVE = {'good','great','excellent','amazing','love','loved','like','liked','perfect','best','useful','happy','satisfied','awesome','nice','worth','recommend','comfortable','easy','clear','fast','beautiful','value','superb','wonderful','fantastic','quality','impressive','works','working'}
NEGATIVE = {'bad','poor','worst','terrible','awful','hate','hated','disappointed','disappointing','broken','defective','damage','damaged','slow','waste','useless','issue','problem','problems','not','never','fail','failed','failure','unhappy','uncomfortable','cheap','return','refund','fake','overpriced','missing','stopped'}
NEGATIONS = {'not','never','no','hardly','isnt','wasnt','dont','didnt','doesnt','cannot','cant'}


def clean_number(value, percent=False):
    if pd.isna(value): return np.nan
    s = str(value).strip().replace(',', '').replace('₹','').replace('Rs.','').replace('INR','').strip()
    if s.lower() in {'', 'nan', 'none', 'null', 'n/a', '-'}: return np.nan
    if percent: s = s.replace('%','')
    s = re.sub(r'[^0-9.\-]', '', s)
    try: return float(s) if s else np.nan
    except ValueError: return np.nan


def clean_frame(frame):
    frame = frame.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing: raise ValueError('Missing required columns: ' + ', '.join(missing))
    for col in ['product_id','product_name','category','about_product','user_id','user_name','review_id','review_title','review_content','img_link','product_link']:
        frame[col] = frame[col].fillna('').astype(str).str.strip()
    for col, pct in [('discounted_price',False),('actual_price',False),('discount_percentage',True),('rating',False),('rating_count',False)]:
        frame[col] = frame[col].apply(lambda x: clean_number(x, pct))
    frame.loc[~frame['rating'].between(0,5), 'rating'] = np.nan
    frame.loc[frame['discount_percentage'].lt(0) | frame['discount_percentage'].gt(100), 'discount_percentage'] = np.nan
    frame.loc[frame['discounted_price'].lt(0), 'discounted_price'] = np.nan
    frame.loc[frame['actual_price'].lt(0), 'actual_price'] = np.nan
    frame.loc[frame['rating_count'].lt(0), 'rating_count'] = np.nan
    frame['main_category'] = frame['category'].apply(lambda x: x.split('|')[0].strip() if x else 'Uncategorized')
    return frame


def load_dataset(path):
    global DF, DATA_SOURCE
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    DF = clean_frame(raw)
    DATA_SOURCE = os.path.basename(path)


def as_float(v):
    return None if pd.isna(v) else float(v)

def as_int(v):
    return None if pd.isna(v) else int(v)

def record_dict(row):
    out = {}
    for col in REQUIRED + ['main_category']:
        if col in row.index:
            val = row[col]
            if col in {'rating','discount_percentage','discounted_price','actual_price','rating_count'}: val = as_float(val)
            else: val = '' if pd.isna(val) else str(val)
            out[col] = val
    return out

def parse_packed(value):
    """Parse a Python/JSON-style list if present; otherwise preserve the whole cell as one value.
    We deliberately do not split raw strings on commas because review text can contain commas."""
    s = str(value or '').strip()
    if not s: return []
    if s.startswith('[') and s.endswith(']'):
        try:
            obj = ast.literal_eval(s)
            if isinstance(obj, (list, tuple)): return [str(x).strip() for x in obj if str(x).strip()]
        except (ValueError, SyntaxError): pass
    return [s]

def sentiment(text):
    words = re.findall(r"[a-z']+", str(text).lower())
    if not words: return {'sentiment':'Neutral','score':0,'explanation':'No review text was provided.'}
    score = 0
    for i, word in enumerate(words):
        if word in POSITIVE or word in NEGATIVE:
            value = 1 if word in POSITIVE else -1
            if any(w in NEGATIONS for w in words[max(0,i-3):i]): value *= -1
            score += value
    # Simple transparent lexicon scoring, not a trained ML model.
    if score > 0: label = 'Positive'
    elif score < 0: label = 'Negative'
    else: label = 'Neutral'
    explanation = {'Positive':'Positive keywords outweigh negative keywords.','Negative':'Negative keywords outweigh positive keywords.','Neutral':'No clear positive or negative keyword signal was found.'}[label]
    return {'sentiment':label,'score':score,'explanation':explanation}

def extract_reviews(frame=None):
    frame = DF if frame is None else frame
    items = []
    for _, row in frame.iterrows():
        # List-formatted cells are parsed only when safely recognizable. Plain cells remain intact.
        titles = parse_packed(row.get('review_title',''))
        contents = parse_packed(row.get('review_content',''))
        ids = parse_packed(row.get('review_id',''))
        # Avoid manufacturing paired reviews from mismatched packed fields.
        if len(contents) > 1 and len(titles) == len(contents):
            pairs = list(zip(titles, contents))
        elif len(contents) == 1:
            pairs = [(titles[0] if titles else '', contents[0])]
        else:
            continue
        for idx, (title, content) in enumerate(pairs):
            if not content.strip(): continue
            result = sentiment((title + ' ' + content).strip())
            items.append({'product_id':row.get('product_id',''), 'product_name':row.get('product_name',''), 'category':row.get('main_category','Uncategorized'), 'review_id':ids[idx] if idx < len(ids) else '', 'review_title':title, 'review_content':content, **result})
    return items

def summary():
    if DF.empty: return {'loaded':False,'dataset_source':DATA_SOURCE,'message':'Upload your Amazon product CSV to begin analysis.'}
    products = DF.drop_duplicates('product_id') if DF['product_id'].ne('').any() else DF
    reviews = extract_reviews()
    ratings = DF['rating'].dropna()
    discounts = DF['discount_percentage'].dropna()
    counts = {s:sum(1 for r in reviews if r['sentiment']==s) for s in ['Positive','Neutral','Negative']}
    return {'loaded':True,'dataset_source':DATA_SOURCE,'rows':int(len(DF)),'unique_products':int(DF.loc[DF['product_id'].ne(''),'product_id'].nunique()),'average_rating':round(float(ratings.mean()),2) if len(ratings) else None,'total_rating_count':int(DF['rating_count'].dropna().sum()) if DF['rating_count'].notna().any() else None,'average_discount':round(float(discounts.mean()),2) if len(discounts) else None,'categories':int(DF.loc[DF['main_category'].ne('Uncategorized'),'main_category'].nunique()),'rating_4_plus':int((DF['rating']>=4).sum()),'sentiment_counts':counts,'review_count':len(reviews),'sentiment_method':'Transparent keyword lexicon; automated predictions may be inaccurate.'}

@app.route('/')
def home(): return render_template('index.html', api_base_url=os.environ.get('API_BASE_URL', '').rstrip('/'))
@app.get('/health')
def health(): return jsonify({'status':'ok','dataset_loaded':not DF.empty,'dataset_source':DATA_SOURCE})
@app.get('/dashboard-summary')
def dashboard_summary(): return jsonify(summary())
@app.get('/products')
def products():
    if DF.empty: return jsonify({'items':[],'total':0,'message':'Upload a CSV dataset to view products.'})
    data = DF.copy()
    q = request.args.get('search','').lower().strip(); cat = request.args.get('category','')
    minr = clean_number(request.args.get('min_rating','')); maxr = clean_number(request.args.get('max_rating',''))
    minp = clean_number(request.args.get('min_price','')); maxp = clean_number(request.args.get('max_price',''))
    mind = clean_number(request.args.get('min_discount','')); maxd = clean_number(request.args.get('max_discount',''))
    if q: data = data[data['product_name'].str.lower().str.contains(q, na=False)]
    if cat: data = data[data['main_category']==cat]
    if not pd.isna(minr): data = data[data['rating']>=minr]
    if not pd.isna(maxr): data = data[data['rating']<=maxr]
    if not pd.isna(minp): data = data[data['discounted_price']>=minp]
    if not pd.isna(maxp): data = data[data['discounted_price']<=maxp]
    if not pd.isna(mind): data = data[data['discount_percentage']>=mind]
    if not pd.isna(maxd): data = data[data['discount_percentage']<=maxd]
    sort = request.args.get('sort','rating_count')
    if sort in data.columns: data = data.sort_values(sort, ascending=sort in {'discounted_price','actual_price','rating'}, na_position='last')
    page = max(1, int(request.args.get('page',1))); per_page = min(100, max(1,int(request.args.get('per_page',30))))
    total = len(data); data = data.iloc[(page-1)*per_page:page*per_page]
    return jsonify({'items':[record_dict(r) for _,r in data.iterrows()],'total':total,'page':page,'per_page':per_page,'categories':sorted(DF['main_category'].dropna().unique().tolist())})
@app.get('/products/<path:product_id>')
def product_detail(product_id):
    rows = DF[DF['product_id']==product_id]
    if rows.empty: return jsonify({'error':'Product not found in the loaded dataset.'}),404
    row = rows.iloc[0]
    return jsonify({'product':record_dict(row),'review_note':'The source dataset provides overall product ratings, not individual 1–5 star rating counts.','reviews':[r for r in extract_reviews() if r['product_id']==product_id]})
@app.get('/rating-analysis')
def rating_analysis():
    if DF.empty: return jsonify({'loaded':False,'message':'Upload a CSV dataset to analyze ratings.'})
    bins = [(0,1,'0–1'),(1,2,'1–2'),(2,3,'2–3'),(3,4,'3–4'),(4,5.000001,'4–5')]
    dist=[{'range':label,'count':int(((DF.rating>=lo)&(DF.rating<hi)).sum())} for lo,hi,label in bins]
    cat=DF.groupby('main_category',dropna=False).rating.mean().dropna().sort_values(ascending=False)
    top=DF.dropna(subset=['rating']).sort_values('rating',ascending=False).head(10)
    low=DF.dropna(subset=['rating']).sort_values('rating',ascending=True).head(10)
    return jsonify({'loaded':True,'distribution':dist,'category_average':[{'category':str(k),'average_rating':round(float(v),2)} for k,v in cat.items()],'top_rated':[record_dict(r) for _,r in top.iterrows()],'lowest_rated':[record_dict(r) for _,r in low.iterrows()]})
@app.get('/category-analysis')
def category_analysis():
    if DF.empty: return jsonify({'loaded':False,'categories':[]})
    grouped=DF.groupby('main_category',dropna=False).agg(products=('product_id','size'),average_rating=('rating','mean'),average_discount=('discount_percentage','mean')).reset_index()
    return jsonify({'categories':[{'category':r.main_category,'products':int(r.products),'average_rating':round(float(r.average_rating),2) if pd.notna(r.average_rating) else None,'average_discount':round(float(r.average_discount),2) if pd.notna(r.average_discount) else None} for r in grouped.itertuples()]})
@app.get('/most-reviewed-products')
def most_reviewed():
    if DF.empty: return jsonify({'items':[]})
    d=DF.sort_values('rating_count',ascending=False,na_position='last').head(10)
    return jsonify({'items':[record_dict(r) for _,r in d.iterrows()]})
@app.get('/review-analysis')
def review_analysis():
    reviews=extract_reviews()
    q=request.args.get('search','').lower().strip(); cat=request.args.get('category',''); sent=request.args.get('sentiment',''); pid=request.args.get('product_id','')
    if q: reviews=[r for r in reviews if q in (r['review_title']+' '+r['review_content']+' '+r['product_name']).lower()]
    if cat: reviews=[r for r in reviews if r['category']==cat]
    if sent: reviews=[r for r in reviews if r['sentiment']==sent]
    if pid: reviews=[r for r in reviews if r['product_id']==pid]
    return jsonify({'items':reviews[:500],'total':len(reviews),'method':'Keyword lexicon. Plain comma-separated packed review cells are not split; list-formatted fields are parsed only when safe.'})
@app.post('/analyze-review')
def analyze_review():
    body=request.get_json(silent=True) or {}; text=(str(body.get('review_text',''))+' '+str(body.get('review_title',''))).strip()
    if not text: return jsonify({'error':'Enter a review title or review text.'}),400
    result=sentiment(text); result['method']='Transparent keyword lexicon (not a trained ML model).'; result['is_dataset_review']=False
    return jsonify(result)
@app.post('/analyze-dataset')
def analyze_dataset():
    global DF, DATA_SOURCE
    if 'file' not in request.files: return jsonify({'error':'Choose a CSV file first.'}),400
    file=request.files['file']
    if not file.filename.lower().endswith('.csv'): return jsonify({'error':'Only CSV files are supported.'}),400
    safe=secure_filename(file.filename) or 'uploaded.csv'; path=os.path.join(UPLOAD_DIR,safe)
    try:
        file.save(path); load_dataset(path)
        s=summary(); s['missing_values']={c:int(DF[c].isna().sum() + (DF[c].astype(str).str.strip()=='').sum()) for c in REQUIRED}
        s['invalid_numeric_fields']={c:int(DF[c].isna().sum()) for c in ['discounted_price','actual_price','discount_percentage','rating','rating_count']}
        s['preview']=[record_dict(r) for _,r in DF.head(5).iterrows()]
        return jsonify(s)
    except Exception as e: return jsonify({'error':str(e)}),400

# Load only a real local dataset when supplied; never create demonstration records.
if os.path.exists(DATA_PATH):
    try: load_dataset(DATA_PATH)
    except Exception as exc: print('Dataset could not be loaded:', exc)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT','8000')), debug=False)
