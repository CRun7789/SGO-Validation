"""
SGO Scorer — Python port of SGOscorer.java from the sortingSGOs project.

Scoring paths (mutually exclusive, determined by NTEE_CD and ACTIVITY):
  - NTEE path:       NTEE_CD starts with "B"
  - No-NTEE path:    no NTEE_CD and ACTIVITY == 31150120
  - Unclassified:    everything else (half-weight penalties)

Hard disqualifiers return 0. Certified SGOs return 100.
After all rows are scored, any non-certified score above 100 is clamped by
subtracting the overage from every non-certified row (same normalization as Java).
"""

import re
import pandas as pd

# ---------------------------------------------------------------------------
# Keyword sets (from SGOscorer.java)
# ---------------------------------------------------------------------------

STRONG_POSITIVE   = {"STO", "SGO", "TUITION", "SCHOLARSHIP", "SCHOLARSHIPS"}
MODERATE_POSITIVE = {"GRANTING", "CHOICE", "EDUCATIONAL"}
WEAK_POSITIVE     = {"EDUCATION", "FUND", "STUDENT", "STUDENTS"}
STRONG_PENALTY    = {"CHURCH", "SISTERS", "BROTHERS", "CHAPTER"}
MODERATE_PENALTY  = {"FAMILY", "LEAGUE", "THEATRE"}

NTEE_CLASS_VALID = {"1000", "1200", "2000"}
ALL_CLASS_VALID  = {"1000", "1200", "1700", "2000", "7000"}

# ---------------------------------------------------------------------------
# Certified SGO lists by state (from NonprofitFinder.java CERTIFIED_BY_STATE)
# Keys are lowercase 2-letter state codes matching IRS STATE column values.
# ---------------------------------------------------------------------------

CERTIFIED_BY_STATE = {
    "al": {
        "Scholarships for Kids, Inc",
        "Alabama Opportunity Scholarship Fund",
        "Rocket City Scholarship Granting Organization, Inc",
        "Children's Tuition Fund of Alabama (ACSI)",
        "Renaissance Scholarships, Inc",
        "C2 Opportunity Scholarships LLC",
        "Deontaye V. Caple Scholarship",
        "Arete Scholars Fund, Inc",
    },
    "ar": {"The Reform Alliance"},
    "az": {
        "!SpecialNeedsScholarships.org",
        "A+ Tuition Assistance",
        "Academic Opportunity of Arizona",
        "Allegiance Acres Microschool Inc",
        "America's Scholarship Konnection Inc",
        "Arizona Adventist Scholarships, Inc.",
        "Arizona Christian Tuition",
        "Arizona Christian School Tuition Organization, Inc.",
        "Arizona Education and Scholarship Opportunity Program",
        "Arizona Education Scholarship Foundation",
        "Arizona Episcopal Schools Foundation",
        "Arizona Independent Schools Scholarship Foundation",
        "Arizona International Academy Scholarship Fund",
        "Arizona Private Education Scholarship Fund, Inc.",
        "Arizona Private School Tuition Organization",
        "Arizona School Choice Trust",
        "Arizona Tuition Connection",
        "Arizona Tuition Organization",
        "Arizona's Catholic Tuition Support Organization (CTSO)",
        "Azura",
        "Best Student Fund",
        "Blessed Sacrament Academy",
        "Brophy Community Foundation",
        "Catalyst Tuition Alliance",
        "Catholic Education Arizona",
        "Chabad Tuition Organization",
        "Christian Scholarship Fund of Arizona",
        "Cochise Christian School Tuition Organization",
        "Community Reinvestment Low Income Based Scholarships",
        "Community Tuition Grant Organization, Inc.",
        "Dream Tuition Scholarship Fund Inc.",
        "Dynamite Montessori Foundation",
        "Financial Assistance for Independent Schools",
        "Greater Arizona Inc.",
        "Institute for Better Education (IBE)",
        "Jewish Education Tax Credit Organization (JETCO)",
        "Jewish Tuition Organization",
        "Montessori Charity Foundation",
        "Northern Arizona Christian School Scholarship Fund",
        "Pappas Kids Schoolhouse Foundation",
        "Private School Tuition Fund 123",
        "Scholarkids",
        "Scholarships for Educational Excellence Foundation",
        "School Choice Arizona",
        "School Tuition Association of Yuma",
        "School Tuition Organization 4 Kidz",
        "Simply STO",
        "Students First Foundation",
        "The Noble Arch Foundation",
        "Sunrise Academy for Students with Special Needs",
        "Tuition Resources Foundation",
        "Valley Tuition Organization",
        "Verde Valley School Tuition Organization",
        "White Mountain Tuition Support Foundation",
        "Yuma's Education Scholarship Fund for Kids.",
    },
    "fl": {
        "A.A.A. Scholarship Foundation- FL, LLC",
        "Step Up For Students",
        "University of Florida Lastinger Center for Learning",
    },
    "ga": {
        "AAA Scholarship Foundation, Inc.",
        "A Pay It Forward Scholarships",
        "Alyn Scholarship Fund, Inc.",
        "Apogee Georgia School Choice Scholarship Fund",
        "Arete Scholars Fund, Inc.",
        "Christian International Counseling & Ministries, Inc.",
        "Creative Community Outreach, INC",
        "Dianne and Friends, Inc.",
        "Georgia's Goal Scholarship Program",
        "Georgia Leadership Foundation, Inc.",
        "Georgia's Student Scholarship Organization SSO (GaSSO)",
        "Georgia's Tax Credit Scholarship Program, Inc.",
        "Golden Dome Scholarship Fund",
        "Grace Point Christian Academy",
        "GRACE Scholars, Inc.",
        "GREAT SSO, Inc.",
        "JAM Community Development Center",
        "Kipp Opportunity Fund",
        "Learning to Serve",
        "New Generation Academy",
        "PACE Scholarship Organization Corp.",
        "Student Scholarship Organization, Inc.",
        "Student Scholarship Organization for Greek Americans",
        "The Georgia Tuition Assistance Program, Inc.",
        "Veritas School of Social Sciences",
        "Vision SSO, Inc.",
        "Wisdom Education Inc.",
    },
    "in": {
        "Community Foundation of Elkhart County",
        "Diocese of Fort Wayne-South Bend",
        "Education Choice Charitable Trust",
        "Indiana Foundation for Education Advancement",
        "Legacy Foundation",
        "Professional Athletes of Indiana",
        "Sagamore Institute Scholarships for Education",
        "Scholarship Granting Organization of Northeast Indiana, Inc.",
        "The Lutheran Scholarship Granting Organization of Indiana, Inc.",
    },
    "ia": {
        "MISSISSIPPI VALLEY SCHOOL TUITIONORGANIZATION INC",
        "SCHOOL TUITION ORGANIZATION OF SOUTHEAST IOWA",
        "NORTH CENTRAL IOWA STO INC",
        "NORTHWEST IOWA CHRISTIAN SCHOOL",
        "HEART OF IOWA SCHOOL TUITION ORGANIZATION INC",
        "LEGACY OF GRACE SCHOOL TUITION ORGANIZATION INC",
        "MONSIGNOR LAFFERTY TUITION FOUNDATION",
        "IOWA LUTHERAN SCHOOL TUITIONORGANIZATION INC",
        "OUR FAITH OUR CHILDREN OUR FUTURE SCHOOL TUITION ORGANIZATION",
        "ROMAN CATHOLIC DIOCESE OF DES MOINES",
        "INDEPENDENT SCHOOL ASSOCIATION OF EASTERN IOWA SCHOOL TUITION ORG",
        "IOWA INDEPENDENT SCHOOL TUITION ORGANIZATION",
    },
    "ks": {
        "ACE Scholarships Kansas",
        "Catholic Education Foundation",
        "Christian Faith Centre, Inc.",
        "Cornerstone Charitable Foundation",
        "Kansas Lutheran Schools Scholarship Foundation, Inc.",
        "The Independent School",
        "Prime Fit Youth Foundation SGO",
        "Renewanation",
        "Scholarships for Catholic Schools, Inc.",
        "Scholarship Granting Fund for Catholic Diocese of Salina",
        "St. Paul Lutheran School Foundation",
        "Support for Catholic Schools, Inc.",
        "Topeka Lutheran School Foundation, Inc.",
    },
    "la": {
        "Arete Scholars Louisiana",
        "Aspiring Scholars Louisiana",
        "Son of a Saint Louisiana",
    },
    "mo": {
        "ACSI Children's Tuition Fund",
        "Agudath Israel of Missouri",
        "Bright Futures Fund",
        "Herzog Tomorrow Foundation",
        "Missouri District – LCMS",
        "Today and Tomorrow Educational Foundation (TTEF)",
    },
    "mt": {
        "Big Sky Community School",
        "Central Education Foundation of Silver Bow",
        "Elevation Foundation, Inc.",
        "Great Falls Central Catholic High School",
        "Holy Spirit Catholic School",
        "Kalispell Montessori Center, Inc.",
        "Manhattan Christian School",
        "Missoula Catholic Schools Foundation",
        "Missoula Christian Montessori School",
        "Montana Leadership Foundation",
        "Our Lady of Lourdes Catholic School",
        "Saint Matthew Parish Series 535",
        "The Headwaters Academy",
        "The Skola",
        "The Summit Lighthouse",
        "The Way Christian School",
        "Valley Christian School",
        "Woodland Montessori School Foundation",
    },
    "nv": {
        "Education Fund of Northern Nevada",
        "Student Choice Fund of Nevada",
        "AAA Scholarships Nevada",
        "America's Scholarship Konnection",
        "Silver State Scholarship",
        "Injured Police Officers Fund",
    },
    "nh": {"Children's Scholarship Fund New Hampshire"},
    "oh": {
        "3 Rivers Scholarship Granting Organization",
        "ABC Ohio Foundation",
        "Akron Chesterton Scholarship Fund",
        "Archbishop Hoban High School SGO",
        "Beaumont School Scholarship Granting Organization",
        "BengalSGO",
        "Bluestone Hibernian Charities",
        "Catholic Education Foundation for the Archdiocese of Cincinnati",
        "Chaminade Julienne Catholic Education Fund",
        "Chesterton Academy of St. Benedict Scholarship Fund",
        "Chesterton Society of St Joseph Scholarship Fund",
        "Christ the Teacher Diocesan Scholarship Fund, Inc.",
        "Christian Education Fund of Allen County",
        "CHRISTIAN HERITAGE EDUCATION FUND",
        "Cincinnati Islamic School SGO",
        "CISE",
        "Dayton Christian SGO",
        "Dayton Reformation Scholarship Granting Organization",
        "Diocesan Education Corporation",
        "Diocese of Toledo Scholarship Fund",
        "Discovery School",
        "FAITH ISLAMIC ACADEMY SCHOLARSHIP FOUNDATION",
        "FCS Scholarship Committee",
        "Forever 49 Foundation",
        "Gabriel SGO Inc.",
        "Global Horizons SGO",
        "Julie Billiart Network Scholarship Granting Organization",
        "Legacy Education Affordability Fund",
        "Lutheran Scholarship Granting Organization of Ohio Inc",
        "Lyceum Scholarship Fund",
        "Magnificat Scholarship Granting Organization",
        "MANSFIELD TEMPLE CHRISTIAN CRUSADER EDUCATION FUND",
        "Mars Hill SGO",
        "Mount Notre Dame SGO",
        "NEHEMIAH EDUCATION FUND, INC.",
        "Nordonia Hills Schools Scholarship Granting Organization",
        "Northside Christian Scholarship Fund",
        "Norwalk Catholic Scholarship Granting Organization",
        "Notre Dame Academy Foundation",
        "Notre Dame Schools Scholarship Granting Organization",
        "Ohio Association of Independent Schools Scholarship Granting Organizations",
        "Ohio Christian Education Network Scholarship Granting Organization",
        "Ohio Christian Scholarship Granting Organization, Inc",
        "Ohio EduCare Inc",
        "Ohio Scholarship Fund",
        "Omega Community Enrichment Foundation",
        "Saint John SGO",
        "Saint Joseph Academy Scholarship Granting Organization",
        "Scholarship Granting Organization of the Catholic Community Foundation",
        "SEHS Scholarship Granting Organization",
        "Servant Partners Inc.",
        "Seton Catholic School Scholarship Granting Organization",
        "Seton Cincinnati SGO",
        "SMDPHS SCHOLARSHIP GRANTING ORGANIZATION",
        "SSMS Scholarship Granting Organization",
        "St. Francis de Sales High School Foundation",
        "St. Ignatius High School Scholarship Granting Organization",
        "St. Joseph Scholarship Fund",
        "St. Ursula Academy Foundation",
        "St. Ursula Academy Scholarship Granting Organization",
        "The Diocese of Youngstown Scholarship Granting Organization",
        "The Juniper School",
        "The Mustard Seed Education Foundation",
        "The Ohio Commodore Scholarship Fund",
        "THE ST JOHNS JESUIT SCHOLARSHIP GRANTING ORGANIZATION",
        "The Way They Should Go Fund",
        "Thunderbird Scholarship Granting Organization",
        "Toledo Christian Schools Foundation",
        "Troy Christian SGO",
        "Ursuline Foundation",
        "Walsh Jesuit High School Scholarship Granting Organization",
        "Xavier-SGO",
    },
    "ok": {
        "Oklahoma Islamic School Foundation",
        "GO for Catholic Schools Inc.",
        "Oklahoma School Choice Scholarship Fund (OSCSP)",
        "Oklahoma Foundation for Excellence",
        "Opportunity Scholarship Fund",
        "Kids' Chance of Oklahoma",
        "Liberty Christian Academy Scholarship Fund",
        "Episcopal School Scholarship Fund",
        "Catholic Schools Opportunity Fund (CSOF)",
        "Crossover Scholarship Fund (CSF)",
        "The Academy of Classical Christian Studies",
    },
    "pa": {
        "Abington Friends School",
        "Academy in Manayunk d/b/a AIM Academy",
        "Academy of Notre Dame de Namur",
        "ACSI Children's Education Fund d/b/a Children's Tuition Fund of Pennsylvania",
        "Advancing Youth Initiative",
        "Agnes Irwin School",
        "Aquinas Academy",
        "ATG Learning Academy",
        "Benchmark School",
        "Berks County Community Foundation",
        "Best of the Batch Foundation",
        "Bridge Educational Foundation",
        "Business Leadership Organized for Catholic Schools (BLOCS)",
        "Buxmont Academy",
        "Byerschool Foundation",
        "C.B. Community Schools",
        "Carnegie Mellon University",
        "Carroll Patriot Educational Fund",
        "Center School",
        "Central Pennsylvania Scholarship Fund",
        "CEO America Lehigh Valley",
        "Children First America Delaware County",
        "Children's Scholarship Fund of Pennsylvania",
        "Children's Scholarship Fund Philadelphia",
        "Christian Life Academy Opportunity Scholarship Fund",
        "Christian School Association of Greater Harrisburg, Inc.",
        "Christian School Association of York",
        "Commonwealth Charitable Management, Inc.",
        "Community Country Day School",
        "Community Foundation of Western PA and Eastern OH",
        "Community Partnership School",
        "Cornerstone Christian Academy",
        "Cristo Rey Philadelphia High School",
        "Crossroads Foundation",
        "Dayspring Christian Academy",
        "Delaware Valley Friends School",
        "Devon Preparatory School",
        "Diocese of Scranton Scholarship Foundation",
        "Discovery Multiple Intelligences Preschool d/b/a Discovery Montessori",
        "Drexel Neumann Academy",
        "Eastern Pennsylvania Scholarship Foundation - Diocese of Allentown",
        "Erie Day School, Inc.",
        "Evangelical Lutheran Church in America",
        "Everence Foundation, Inc. d/b/a Mennonite Foundation",
        "Faith Builders Educational Programs, Inc.",
        "Faith Christian School Association of Monroe County, Inc.",
        "Falk Laboratory School of the University of Pittsburgh",
        "Family Choice Scholarship Program of the PA Family Institute",
        "Foundation for Catholic Education",
        "Foundation for Jewish Day Schools of Greater Philadelphia",
        "Frankford Friends School",
        "French International School of Philadelphia",
        "Friends' Central School",
        "Friends Council on Education",
        "Friends School Haverford",
        "Friends Select School",
        "Fund for the Advancement of Minorities through Education, Inc. (FAME)",
        "George School",
        "Germantown Academy (Public School of Germantown)",
        "Germantown Friends School",
        "Gesu School, Inc.",
        "Girard College Foundation",
        "Gladwyne Montessori School",
        "Go Forward Education Foundation, Inc.",
        "Greater Philadelphia Association for Recovery Education",
        "Greene Street Friends School",
        "Greene Towne School",
        "Gwynedd Mercy Academy High School",
        "Harrisburg Academy",
        "Holy Child School at Rosemont",
        "Holy Family Foundation",
        "Holy Ghost Preparatory School",
        "Hope Partnership for Education",
        "Imani Christian Academy",
        "Indian Creek Valley Christian Family and Children's Center",
        "Jewish Federation of the Lehigh Valley",
        "Jubilee School",
        "Junior Achievement of Western PA",
        "Keystone Christian Education Association",
        "KidsPeace Corp.",
        "La Salle Academy",
        "La Salle College High School Scholarship Fund",
        "Lancaster Country Day School",
        "Lancaster County Christian School",
        "Liguori Academy, Inc.",
        "LOGAN Hope",
        "Londonderry School",
        "Malvern Preparatory School",
        "Mastery Charter Schools Foundation",
        "McGlynn Center",
        "Meadowbrook Christian School Scholarship Organization",
        "Media-Providence Friends School, Inc.",
        "Mercy Vocational High School",
        "Mercyhurst Preparatory School",
        "Merion Mercy Academy",
        "MMI Preparatory School",
        "Moravian Academy",
        "Mount Saint Joseph Academy",
        "Nativity School of Harrisburg",
        "NativityMiguel School of Scranton",
        "Neumann Scholarship Foundation",
        "Newtown Friends School",
        "Our Lady of the Sacred Heart High School",
        "Penngift Foundation, Inc.",
        "Philadelphia Youth Orchestra",
        "Pittsburgh Jewish Educational Improvement Foundation",
        "PJHS Scholarship Organization (St. Joe's Prep & Scranton Prep)",
        "Plymouth Meeting Friends School",
        "Pocono Mountains United Way",
        "Poise Foundation",
        "Quaker School at Horsham",
        "Sacred Heart Academy Bryn Mawr",
        "Saint James School",
        "Salvaggio Academy",
        "Scholarship Partners Foundation",
        "Scholastic Opportunity Scholarship Fund (SOS)",
        "Sewickley Academy",
        "Shady Side Academy",
        "Silverback Educational Foundation for the Arts, Dance & Athletics",
        "Spanish Scholarship Fund",
        "Springside Chestnut Hill Academy",
        "St. Edmund's Academy",
        "STAR Foundation",
        "Stratford Friends School",
        "The Baldwin School",
        "The Campus Laboratory School of Carlow University",
        "The Church Farm School",
        "The Circle School",
        "The Ellis School",
        "The Episcopal Academy",
        "The Glen Montessori School",
        "The Grayson School",
        "The Gureghian Charitable Foundation",
        "The Haverford School",
        "The Hill Top Preparatory School, Inc.",
        "The Hillside School",
        "The Janus School",
        "The Joshua Group",
        "The Learning Lamp, Inc.",
        "The Meadowbrook School",
        "The Miquon School",
        "The Neighborhood Academy",
        "The Phelps School",
        "The Philadelphia School",
        "The Samuel School",
        "The Shipley School",
        "The Stone Independent School",
        "The Swain School, Inc.",
        "The University School d/b/a Tus, Inc.",
        "The Woodlynde School Corporation",
        "United Way of Lackawanna and Wayne Counties",
        "United Way of Wyoming Valley",
        "Upland Country Day School",
        "Valley Forge Military Academy Foundation",
        "Villa Maria Academy (Malvern)",
        "Villa Maria Cathedral Preparatory Catholic School System",
        "Waldorf School of Pittsburgh",
        "Washington County Community Foundation",
        "West Chester Friends School",
        "William Penn Charter School",
        "Winchester Thurston School",
        "Wyndcroft School",
        "Wyoming Seminary",
        "Yeshiva Beth Moshe NEPA Jewish Educational Scholarship Fund",
        "York College Scholarship Organization of Pennsylvania",
    },
    "ri": {
        "Achievement for Children with Challenges Empowered by School Scholarships (ACCESS)",
        "Children's Tuition Fund of Rhode Island",
        "F.A.C.E. of Rhode Island",
        "Scholarships to Economically Poor Students (STEPS)",
        "STAR SCHOLARS OPPORTUNITY PROGRAM",
        "Teach Initiative",
        "The Foundation for Rhode Island Day Schools",
    },
    "sc": {"Exceptional SC"},
    "sd": {"South Dakota Partners in Education"},
    "ut": {"Children First Education Fund"},
    "va": {
        "Anabaptist Scholarship Foundation of Virginia",
        "Anna Julia Cooper Scholarship Foundation",
        "Association of Christian Schools International (ACSI Children's Tuition Fund)",
        "Atlantic Shores Tuition Foundation",
        "Boys Home of Virginia",
        "Buffolo Creek Boys School",
        "Carlisle School",
        "Rise Richmond",
        "Diocese of Arlington Scholarship Foundation, Inc.",
        "Dunlap Garrick Christian Community Foundation",
        "Elijah House Academy",
        "Fishburne-Hudgins Educational Foundation",
        "Fork Union Military Academy Foundation",
        "Foundation for Educational & Developmental Opportunity",
        "Great Aspirations Scholarship Program (GRASP)",
        "Hague School Foundation",
        "Imago Dei Scholarship Foundation",
        "Jackson-Feild Homes",
        "Leadership International, A Charitable Trust",
        "Liberty Christian Academy, Inc.",
        "Lunenburg-Nottoway Educational Foundation",
        "McMahon-Parater Foundation for Education",
        "New Covenant Schools",
        "North Cross School",
        "Potomac Conference Education Fund",
        "RENEWANATION",
        "Richmond Jewish Foundation",
        "St. Andrew's School",
        "The Community Foundation of Harrisonburg and Rockingham County",
        "The Community Foundation of the Rappahannock River Region",
        "The Nansemond-Suffolk Academy Educational Foundation",
        "The Rural Education Foundation",
        "Tidewater Jewish Foundation, Inc.",
        "Virginia Foundation for LD Students",
        "Hampton Roads International Montessori School",
    },
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _n(s):
    """Normalize a string: uppercase, strip non-alphanumeric (except spaces), collapse spaces."""
    if not s:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9 ]', '', str(s).upper())).strip()


def _to_int(val, default=0):
    try:
        return int(str(val).strip().split('.')[0])
    except Exception:
        return default


# Pre-normalize all certified names for fast lookup: state_code -> set of normalized names
_CERTIFIED_NORMALIZED = {
    state: {_n(name) for name in names}
    for state, names in CERTIFIED_BY_STATE.items()
}


def _score_names(name):
    words = re.split(r'[^A-Z0-9]+', name.upper())
    has_strong = any(w in STRONG_POSITIVE for w in words)
    score = 0
    for w in words:
        if w in STRONG_POSITIVE:
            score += 2
        elif w in MODERATE_POSITIVE and has_strong:
            score += 1
        elif w in WEAK_POSITIVE:
            score += 1
        elif w in STRONG_PENALTY:
            score -= 2
        elif w in MODERATE_PENALTY:
            score -= 1
    return score


def _score_ntee_path(ntee, affiliation, group, foundation, cls_str, activity):
    score = 0
    if ntee == "B82":
        score += 50
    elif ntee in ("B12", "B90"):
        score += 35
    else:
        score += 5

    score += 15 if activity == 0 else -50
    score += 10 if affiliation == 3 else -15
    score += 10 if group == 0 else -10

    if foundation in (15, 16):
        score += 10
    elif foundation == 10:
        score += 5
    else:
        score -= 15

    score += 5 if cls_str in NTEE_CLASS_VALID else -10
    return score


def _score_no_ntee_path(affiliation, group, foundation, cls_str):
    score = 50
    score += 15 if affiliation == 9 else -10
    score += 15 if group == 928 else -5

    if foundation in (15, 16):
        score += 10
    elif foundation == 10:
        score += 5
    else:
        score -= 15

    if cls_str == "1700":
        score += 5
    elif cls_str not in ALL_CLASS_VALID:
        score -= 10
    return score


def _score_unclassified_path(affiliation, group, foundation, cls_str):
    score = -20

    if foundation in (15, 16):
        score += 5
    elif foundation == 10:
        score += 2
    else:
        score -= 7

    score += 2 if cls_str in ALL_CLASS_VALID else -5
    score += 5 if affiliation in (3, 9) else -7
    score += 5 if group in (0, 928) else -5
    return score


def _score_revenue(revenue_amt, income_amt):
    if revenue_amt > 0 and income_amt > 0:
        return 5
    if revenue_amt == 0 and income_amt == 0:
        return -5
    return 0


def _score_row(row, certified_for_state):
    """
    Score a single row.

    Returns (score: int, path: str) where path is one of:
      "CERTIFIED", "DISQUALIFIED", "NTEE", "NO_NTEE", "UNCLASSIFIED"

    Path is used by the caller to apply the correct combined-score weighting:
      CERTIFIED / NTEE  → 50/50 average with irs_filter_score
      NO_NTEE / UNCLASSIFIED / DISQUALIFIED → 65% irs_filter_score + 35% sgo_scorer_score
    """
    name = str(row.get('NAME', '') or '')
    norm_name = _n(name)

    # Determine the scoring path based on NTEE (used for weighting even for certified orgs)
    ntee     = str(row.get('NTEE_CD', '') or '').strip()
    has_ntee = bool(ntee)
    activity = _to_int(row.get('ACTIVITY'))

    if has_ntee and ntee.startswith('B'):
        natural_path = 'NTEE'
    elif not has_ntee and activity == 31150120:
        natural_path = 'NO_NTEE'
    else:
        natural_path = 'UNCLASSIFIED'

    if norm_name in certified_for_state:
        return 100, 'CERTIFIED'

    deductibility    = _to_int(row.get('DEDUCTIBILITY'))
    pf_filing_req_cd = _to_int(row.get('PF_FILING_REQ_CD'))
    subsection       = _to_int(row.get('SUBSECTION'))

    if deductibility != 1 or pf_filing_req_cd != 0 or subsection != 3:
        return 0, 'DISQUALIFIED'

    affiliation = _to_int(row.get('AFFILIATION'))
    group       = _to_int(row.get('GROUP'))
    foundation  = _to_int(row.get('FOUNDATION'))
    cls_str     = str(row.get('CLASSIFICATION', '') or '').strip()
    revenue_amt = _to_int(row.get('REVENUE_AMT'))
    income_amt  = _to_int(row.get('INCOME_AMT'))

    if natural_path == 'NTEE':
        score = _score_ntee_path(ntee, affiliation, group, foundation, cls_str, activity)
    elif natural_path == 'NO_NTEE':
        score = _score_no_ntee_path(affiliation, group, foundation, cls_str)
    else:
        score = _score_unclassified_path(affiliation, group, foundation, cls_str)

    score += _score_names(name)
    score += _score_revenue(revenue_amt, income_amt)
    return score, natural_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_sgo_scores(df):
    """
    Compute sortingSGOs scorer scores for every row in df.

    Operates on the already-filtered dataset (output of filter_organizations +
    filter_by_name) — not the full IRS download.

    Returns a DataFrame with two columns:
      sgo_scorer_score  int   0-100, normalized so no non-certified org exceeds 100
      scoring_path      str   CERTIFIED | NTEE | NO_NTEE | UNCLASSIFIED | DISQUALIFIED
    """
    scores = []
    paths  = []
    is_certified_flags = []

    for _, row in df.iterrows():
        state_key = str(row.get('STATE', '') or '').strip().lower()
        certified_set = _CERTIFIED_NORMALIZED.get(state_key, set())
        s, path = _score_row(row, certified_set)
        scores.append(s)
        paths.append(path)
        is_certified_flags.append(path == 'CERTIFIED')

    scores_series = pd.Series(scores, index=df.index, dtype=int)

    # Normalize: subtract overage from non-certified rows if any exceed 100
    non_cert_mask = pd.Series([not f for f in is_certified_flags], index=df.index)
    non_cert_scores = scores_series[non_cert_mask]
    if len(non_cert_scores) > 0:
        max_score = non_cert_scores.max()
        if max_score > 100:
            overage = max_score - 100
            scores_series = scores_series.where(~non_cert_mask, scores_series - overage)

    return pd.DataFrame({
        'sgo_scorer_score': scores_series,
        'scoring_path':     pd.Series(paths, index=df.index),
    })
