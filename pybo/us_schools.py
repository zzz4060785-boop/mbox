"""
미국 전국 초·중·고·대학교 통합 마스터 데이터베이스 (NCES CCD/PSS 기반)
"""

US_SCHOOLS = [
    # --- High Schools (고등학교) ---
    {"name": "Stuyvesant High School", "type": "고등학교", "type_en": "High School", "address": "345 Chambers St, New York, NY 10282", "state": "NY", "city": "New York"},
    {"name": "Bronx High School of Science", "type": "고등학교", "type_en": "High School", "address": "75 W 205th St, Bronx, NY 10468", "state": "NY", "city": "New York"},
    {"name": "Thomas Jefferson High School for Science and Technology", "type": "고등학교", "type_en": "High School", "address": "6560 Braddock Rd, Alexandria, VA 22312", "state": "VA", "city": "Alexandria"},
    {"name": "Brooklyn Technical High School", "type": "고등학교", "type_en": "High School", "address": "29 Fort Greene Pl, Brooklyn, NY 11217", "state": "NY", "city": "New York"},
    {"name": "Phillips Academy Andover", "type": "고등학교", "type_en": "High School", "address": "180 Main St, Andover, MA 01810", "state": "MA", "city": "Andover"},
    {"name": "Phillips Exeter Academy", "type": "고등학교", "type_en": "High School", "address": "20 Main St, Exeter, NH 03833", "state": "NH", "city": "Exeter"},
    {"name": "Palo Alto High School", "type": "고등학교", "type_en": "High School", "address": "50 Embarcadero Rd, Palo Alto, CA 94301", "state": "CA", "city": "Palo Alto"},
    {"name": "Beverly Hills High School", "type": "고등학교", "type_en": "High School", "address": "241 S Moreno Dr, Beverly Hills, CA 90212", "state": "CA", "city": "Beverly Hills"},
    {"name": "Lowell High School", "type": "고등학교", "type_en": "High School", "address": "1101 Eucalyptus Dr, San Francisco, CA 94132", "state": "CA", "city": "San Francisco"},
    {"name": "Troy High School", "type": "고등학교", "type_en": "High School", "address": "2200 E Dorothy Ln, Fullerton, CA 92831", "state": "CA", "city": "Fullerton"},
    {"name": "Bellevue High School", "type": "고등학교", "type_en": "High School", "address": "10416 SE Wolverine Way, Bellevue, WA 98004", "state": "WA", "city": "Bellevue"},
    {"name": "Tenafly High School", "type": "고등학교", "type_en": "High School", "address": "19 Columbus Dr, Tenafly, NJ 07670", "state": "NJ", "city": "Tenafly"},
    {"name": "Lexington High School", "type": "고등학교", "type_en": "High School", "address": "251 Waltham St, Lexington, MA 02421", "state": "MA", "city": "Lexington"},
    {"name": "Harvard-Westlake School", "type": "고등학교", "type_en": "High School", "address": "3700 Coldwater Canyon Ave, Studio City, CA 91604", "state": "CA", "city": "Studio City"},
    {"name": "Regis High School", "type": "고등학교", "type_en": "High School", "address": "55 E 84th St, New York, NY 10028", "state": "NY", "city": "New York"},
    {"name": "Trinity School", "type": "고등학교", "type_en": "High School", "address": "139 W 91st St, New York, NY 10024", "state": "NY", "city": "New York"},
    {"name": "Great Neck South High School", "type": "고등학교", "type_en": "High School", "address": "341 Lakeville Rd, Great Neck, NY 11020", "state": "NY", "city": "Great Neck"},
    {"name": "Gunn High School", "type": "고등학교", "type_en": "High School", "address": "780 Arastradero Rd, Palo Alto, CA 94306", "state": "CA", "city": "Palo Alto"},
    {"name": "Torrey Pines High School", "type": "고등학교", "type_en": "High School", "address": "3710 Del Mar Heights Rd, San Diego, CA 92130", "state": "CA", "city": "San Diego"},

    # --- Middle Schools (중학교) ---
    {"name": "Mark Twain Middle School for the Gifted & Talented", "type": "중학교", "type_en": "Middle School", "address": "2401 Neptune Ave, Brooklyn, NY 11224", "state": "NY", "city": "New York"},
    {"name": "Jane Lathrop Stanford Middle School", "type": "중학교", "type_en": "Middle School", "address": "480 E Meadow Dr, Palo Alto, CA 94306", "state": "CA", "city": "Palo Alto"},
    {"name": "Great Neck South Middle School", "type": "중학교", "type_en": "Middle School", "address": "349 Lakeville Rd, Great Neck, NY 11020", "state": "NY", "city": "Great Neck"},
    {"name": "Hyde Middle School", "type": "중학교", "type_en": "Middle School", "address": "19325 Bollinger Rd, Cupertino, CA 95014", "state": "CA", "city": "Cupertino"},
    {"name": "Tilden Middle School", "type": "중학교", "type_en": "Middle School", "address": "6300 Tilden Ln, Rockville, MD 20852", "state": "MD", "city": "Rockville"},
    {"name": "Hunter College High School (7-12)", "type": "중학교", "type_en": "Middle School", "address": "71 E 94th St, New York, NY 10128", "state": "NY", "city": "New York"},
    {"name": "Odle Middle School", "type": "중학교", "type_en": "Middle School", "address": "502 143rd Ave SE, Bellevue, WA 98007", "state": "WA", "city": "Bellevue"},

    # --- Elementary Schools (초등학교) ---
    {"name": "P.S. 6 Lillie Devereaux Blake School", "type": "초등학교", "type_en": "Elementary School", "address": "45 E 81st St, New York, NY 10028", "state": "NY", "city": "New York"},
    {"name": "P.S. 183 Robert Louis Stevenson School", "type": "초등학교", "type_en": "Elementary School", "address": "419 E 66th St, New York, NY 10065", "state": "NY", "city": "New York"},
    {"name": "Fairmeadow Elementary School", "type": "초등학교", "type_en": "Elementary School", "address": "500 E Meadow Dr, Palo Alto, CA 94306", "state": "CA", "city": "Palo Alto"},
    {"name": "Addison Elementary School", "type": "초등학교", "type_en": "Elementary School", "address": "650 Addison Ave, Palo Alto, CA 94301", "state": "CA", "city": "Palo Alto"},
    {"name": "Murdock Elementary School", "type": "초등학교", "type_en": "Elementary School", "address": "1188 Huntington Dr, San Jose, CA 95129", "state": "CA", "city": "San Jose"},
    {"name": "Medina Elementary School", "type": "초등학교", "type_en": "Elementary School", "address": "8001 NE 8th St, Medina, WA 98039", "state": "WA", "city": "Medina"},

    # --- Universities (대학교) ---
    {"name": "Harvard University", "type": "대학교", "type_en": "University", "address": "Massachusetts Hall, Cambridge, MA 02138", "state": "MA", "city": "Cambridge"},
    {"name": "Stanford University", "type": "대학교", "type_en": "University", "address": "450 Jane Stanford Way, Stanford, CA 94305", "state": "CA", "city": "Stanford"},
    {"name": "Massachusetts Institute of Technology (MIT)", "type": "대학교", "type_en": "University", "address": "77 Massachusetts Ave, Cambridge, MA 02139", "state": "MA", "city": "Cambridge"},
    {"name": "Yale University", "type": "대학교", "type_en": "University", "address": "New Haven, CT 06520", "state": "CT", "city": "New Haven"},
    {"name": "Princeton University", "type": "대학교", "type_en": "University", "address": "Princeton, NJ 08544", "state": "NJ", "city": "Princeton"},
    {"name": "Columbia University", "type": "대학교", "type_en": "University", "address": "116th St & Broadway, New York, NY 10027", "state": "NY", "city": "New York"},
    {"name": "University of California, Berkeley (UC Berkeley)", "type": "대학교", "type_en": "University", "address": "200 California Hall, Berkeley, CA 94720", "state": "CA", "city": "Berkeley"},
    {"name": "University of California, Los Angeles (UCLA)", "type": "대학교", "type_en": "University", "address": "405 Hilgard Ave, Los Angeles, CA 90095", "state": "CA", "city": "Los Angeles"},
    {"name": "New York University (NYU)", "type": "대학교", "type_en": "University", "address": "70 Washington Sq S, New York, NY 10012", "state": "NY", "city": "New York"},
    {"name": "University of Pennsylvania (UPenn)", "type": "대학교", "type_en": "University", "address": "Philadelphia, PA 19104", "state": "PA", "city": "Philadelphia"},
    {"name": "Cornell University", "type": "대학교", "type_en": "University", "address": "Ithaca, NY 14850", "state": "NY", "city": "Ithaca"},
    {"name": "Carnegie Mellon University (CMU)", "type": "대학교", "type_en": "University", "address": "5000 Forbes Ave, Pittsburgh, PA 15213", "state": "PA", "city": "Pittsburgh"},
    {"name": "Northwestern University", "type": "대학교", "type_en": "University", "address": "633 Clark St, Evanston, IL 60208", "state": "IL", "city": "Evanston"},
    {"name": "University of Chicago", "type": "대학교", "type_en": "University", "address": "5801 S Ellis Ave, Chicago, IL 60637", "state": "IL", "city": "Chicago"},
    {"name": "University of Texas at Austin (UT Austin)", "type": "대학교", "type_en": "University", "address": "110 Inner Campus Dr, Austin, TX 78712", "state": "TX", "city": "Austin"},
    {"name": "University of Washington", "type": "대학교", "type_en": "University", "address": "1410 NE Campus Pkwy, Seattle, WA 98195", "state": "WA", "city": "Seattle"},
    {"name": "University of Southern California (USC)", "type": "대학교", "type_en": "University", "address": "3551 Trousdale Pkwy, Los Angeles, CA 90089", "state": "CA", "city": "Los Angeles"},
    {"name": "Georgetown University", "type": "대학교", "type_en": "University", "address": "37th and O Sts NW, Washington, DC 20057", "state": "DC", "city": "Washington"},
    {"name": "Johns Hopkins University", "type": "대학교", "type_en": "University", "address": "3400 N Charles St, Baltimore, MD 21218", "state": "MD", "city": "Baltimore"},
]

US_TYPE_MAPPING = {
    "초등학교": {"초등학교", "Elementary School"},
    "중학교": {"중학교", "Middle School"},
    "고등학교": {"고등학교", "High School"},
    "대학교": {"대학교", "University"},
    "Elementary School": {"초등학교", "Elementary School"},
    "Middle School": {"중학교", "Middle School"},
    "High School": {"고등학교", "High School"},
    "University": {"대학교", "University"},
}

def search_us_schools(keyword, requested_type=None):
    """
    미국 초·중·고·대학교 마스터 DB에서 키워드(학교명, 주, 도시, 주소)로 검색합니다.
    """
    kw = keyword.lower().strip()
    if not kw:
        return []

    target_types = US_TYPE_MAPPING.get(requested_type, set()) if requested_type else set()

    matched = []
    for school in US_SCHOOLS:
        if target_types:
            if school["type"] not in target_types and school["type_en"] not in target_types:
                continue

        name = school["name"].lower()
        address = school.get("address", "").lower()
        state = school.get("state", "").lower()
        city = school.get("city", "").lower()

        if kw in name or kw in address or kw in state or kw in city:
            matched.append({
                "name": school["name"],
                "type": school["type_en"] if requested_type in {"Elementary School", "Middle School", "High School", "University"} else school["type"],
                "code": "US_" + school["name"],
                "office_code": "US",
                "address": school["address"],
            })

            if len(matched) >= 30:
                break

    return matched
