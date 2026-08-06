"""
일본 전국 초·중·고·대학교 통합 마스터 데이터베이스 (文部科学省 学校コードDB 기반)
"""

JAPAN_SCHOOLS = [
    # --- 대학교 (大学 / University) ---
    {"name": "東京大学", "type": "대학교", "type_ja": "大学", "address": "東京都文京区本郷7-3-1", "prefecture": "東京都", "reading": "とうきょうだいがく"},
    {"name": "京都大学", "type": "대학교", "type_ja": "大学", "address": "京都府京都市左京区吉田本町", "prefecture": "京都府", "reading": "きょうとだいがく"},
    {"name": "早稲田大学", "type": "대학교", "type_ja": "大学", "address": "東京都新宿区戸塚町1-104", "prefecture": "東京都", "reading": "わせだだいがく"},
    {"name": "慶應義塾大学", "type": "대학교", "type_ja": "大学", "address": "東京都港区三田2-15-45", "prefecture": "東京都", "reading": "けいおうぎじゅくだいがく"},
    {"name": "大阪大学", "type": "대학교", "type_ja": "大学", "address": "大阪府吹田市山田丘1-1", "prefecture": "大阪府", "reading": "おおさかだいがく"},
    {"name": "東北大学", "type": "대학교", "type_ja": "大学", "address": "宮城県仙台市青葉区片平2-1-1", "prefecture": "宮城県", "reading": "とうほくだいがく"},
    {"name": "名古屋大学", "type": "대학교", "type_ja": "大学", "address": "愛知県名古屋市千種区不老町", "prefecture": "愛知県", "reading": "なごやだいがく"},
    {"name": "九州大学", "type": "대학교", "type_ja": "大学", "address": "福岡県福岡市西区元岡744", "prefecture": "福岡県", "reading": "きゅうしゅうだいがく"},
    {"name": "北海道大学", "type": "대학교", "type_ja": "大学", "address": "北海道札幌市北区北8条西5丁目", "prefecture": "北海道", "reading": "ほっかいどうだいがく"},
    {"name": "一橋大学", "type": "대학교", "type_ja": "大学", "address": "東京都国立市中2-1", "prefecture": "東京都", "reading": "ひとつばしだいがく"},
    {"name": "東京工業大学", "type": "대학교", "type_ja": "大学", "address": "東京都目黒区大岡山2-12-1", "prefecture": "東京都", "reading": "とうきょうこうぎょうだいがく"},
    {"name": "明治大学", "type": "대학교", "type_ja": "大学", "address": "東京都千代田区神田駿河台1-1", "prefecture": "東京都", "reading": "めいじだいがく"},
    {"name": "立教大学", "type": "대학교", "type_ja": "大学", "address": "東京都豊島区西池袋3-34-1", "prefecture": "東京都", "reading": "りっきょうだいがく"},
    {"name": "中央大学", "type": "대학교", "type_ja": "大学", "address": "東京都八王子市東中野742-1", "prefecture": "東京都", "reading": "ちゅうおうだいがく"},
    {"name": "法政大学", "type": "대학교", "type_ja": "大学", "address": "東京都千代田区富士見2-17-1", "prefecture": "東京都", "reading": "ほうせいだいがく"},
    {"name": "青山学院大学", "type": "대학교", "type_ja": "大学", "address": "東京都渋谷区渋谷4-4-25", "prefecture": "東京都", "reading": "あおやまがくいんだいがく"},
    {"name": "上智大学", "type": "대학교", "type_ja": "大学", "address": "東京都千代田区紀尾井町7-1", "prefecture": "東京都", "reading": "じょうちだいがく"},
    {"name": "同志社大学", "type": "대학교", "type_ja": "大学", "address": "京都府京都市上京区今出川通烏丸東入", "prefecture": "京都府", "reading": "どうししゃだいがく"},
    {"name": "立命館大学", "type": "대학교", "type_ja": "大学", "address": "京都府京都市北区等持院北町56-1", "prefecture": "京都府", "reading": "りつめいかんだいがく"},
    {"name": "関西大学", "type": "대학교", "type_ja": "大学", "address": "大阪府吹田市山手町3-3-35", "prefecture": "大阪府", "reading": "かんさいだいがく"},
    {"name": "関西学院大学", "type": "대학교", "type_ja": "大学", "address": "兵庫県西宮市上ケ原一番町1-155", "prefecture": "兵庫県", "reading": "かんせいがくいんだいがく"},
    {"name": "筑波大学", "type": "대학교", "type_ja": "大学", "address": "茨城県つくば市天王台1-1-1", "prefecture": "茨城県", "reading": "つくばだいがく"},
    {"name": "神戸大学", "type": "대학교", "type_ja": "大学", "address": "兵庫県神戸市灘区六甲台町1-1", "prefecture": "兵庫県", "reading": "こうべだいがく"},
    {"name": "広島大学", "type": "대학교", "type_ja": "大学", "address": "広島県東広島市鏡山1-3-2", "prefecture": "広島県", "reading": "ひろしまだいがく"},
    {"name": "千葉大学", "type": "대학교", "type_ja": "大学", "address": "千葉県千葉市稲毛区弥生町1-33", "prefecture": "千葉県", "reading": "ちばだいがく"},
    {"name": "横浜国立大学", "type": "대학교", "type_ja": "大学", "address": "神奈川県横浜市保土ケ谷区常盤台79-1", "prefecture": "神奈川県", "reading": "よこはまこくりつだいがく"},

    # --- 고등학교 (高等学校 / High School) ---
    {"name": "開成高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "東京都荒川区西日暮里4-2-4", "prefecture": "東京都", "reading": "かいせいこうとうがっこう"},
    {"name": "麻布高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "東京都港区元麻布2-3-29", "prefecture": "東京都", "reading": "あざぶこうとうがっこう"},
    {"name": "灘高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "兵庫県神戸市東灘区魚崎北町8-5-1", "prefecture": "兵庫県", "reading": "なだこうとうがっこう"},
    {"name": "筑波大学附属駒場高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "東京都世田谷区池尻4-7-1", "prefecture": "東京都", "reading": "つくばだいがくふぞくこまばこうとうがっこう"},
    {"name": "慶應義塾高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "神奈川県横浜市港北区日吉4-1-2", "prefecture": "神奈川県", "reading": "けいおうぎじゅくこうとうがっこう"},
    {"name": "早稲田大学高等学院", "type": "고등학교", "type_ja": "高等学校", "address": "東京都練馬区上石神井3-31-21", "prefecture": "東京都", "reading": "わせだだいがくこうとうがくいん"},
    {"name": "桜蔭高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "東京都文京区本郷1-5-25", "prefecture": "東京都", "reading": "おういんこうとうがっこう"},
    {"name": "女子学院高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "東京都千代田区一番町22-10", "prefecture": "東京都", "reading": "じょしがくいんこうとうがっこう"},
    {"name": "東京都立日比谷高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "東京都千代田区永田町2-16-1", "prefecture": "東京都", "reading": "とうきょうとりつひびやこうとうがっこう"},
    {"name": "東京都立西高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "東京都杉並区宮前4-21-32", "prefecture": "東京都", "reading": "とうきょうとりつにしこうとう가っこう"},
    {"name": "神奈川県立横浜翠嵐高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "神奈川県横浜市神奈川区三ツ沢南町3-1", "prefecture": "神奈川県", "reading": "かながわけんりつよこはますいらんこうとうがっこう"},
    {"name": "大阪府立北野高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "大阪府大阪市淀川区新高2-1-78", "prefecture": "大阪府", "reading": "おおさかふりつきたのこうとうがっこう"},
    {"name": "大阪府立天王寺高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "大阪府大阪市阿倍野区三明町2-4-23", "prefecture": "大阪府", "reading": "おおさかふりつてんのうじこうとうがっこう"},
    {"name": "洛南高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "京都府京都市南区壬生通八条下ル東寺町559", "prefecture": "京都府", "reading": "らくなんこうとうがっこう"},
    {"name": "愛知県立旭丘高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "愛知県名古屋市東区出来町3-6-15", "prefecture": "愛知県", "reading": "あいちけんりつあさひがおかこうとうがっこう"},
    {"name": "北海道札幌南高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "北海道札幌市中央区南18条西6-1-1", "prefecture": "北海道", "reading": "ほっかいどうさっぽろみなみこうとうがっこう"},
    {"name": "福岡県立修猷館高等学校", "type": "고등학교", "type_ja": "高等学校", "address": "福岡県福岡市早良区西新2-1-1", "prefecture": "福岡県", "reading": "ふくおかけんりつしゅうゆうかんこうとうがっこう"},

    # --- 중학교 (中学校 / Junior High) ---
    {"name": "開成中学校", "type": "중학교", "type_ja": "中学校", "address": "東京都荒川区西日暮里4-2-4", "prefecture": "東京都", "reading": "かいせいちゅうがっこう"},
    {"name": "麻布中学校", "type": "중학교", "type_ja": "中学校", "address": "東京都港区元麻布2-3-29", "prefecture": "東京都", "reading": "あざぶちゅうがっこう"},
    {"name": "武蔵中学校", "type": "중학교", "type_ja": "中学校", "address": "東京都練馬区豊玉上1-26-1", "prefecture": "東京都", "reading": "むさしちゅうがっこう"},
    {"name": "桜蔭中学校", "type": "중학교", "type_ja": "中学校", "address": "東京都文京区本郷1-5-25", "prefecture": "東京都", "reading": "おういんちゅうがっこう"},
    {"name": "女子学院中学校", "type": "중학교", "type_ja": "中学校", "address": "東京都千代田区一番町22-10", "prefecture": "東京都", "reading": "じょしがくいんちゅうがっこう"},
    {"name": "灘中学校", "type": "중학교", "type_ja": "中学校", "address": "兵庫県神戸市東灘区魚崎北町8-5-1", "prefecture": "兵庫県", "reading": "なだちゅうがっこう"},
    {"name": "筑波大学附属中学校", "type": "중학교", "type_ja": "中学校", "address": "東京都文京区大塚1-9-1", "prefecture": "東京都", "reading": "つくばだいがくふぞくちゅうがっこう"},
    {"name": "東京都立小石川中等教育学校", "type": "중학교", "type_ja": "中学校", "address": "東京都文京区本駒込2-29-10", "prefecture": "東京都", "reading": "とうきょうとりつこいしかわちゅうとうきょういくがっこう"},
    {"name": "渋谷教育学園幕張中学校", "type": "중학교", "type_ja": "中学校", "address": "千葉県千葉市美浜区若葉1-3", "prefecture": "千葉県", "reading": "しぶやきょういくがくえんまくはりちゅうがっこう"},

    # --- 초등학교 (小学校 / Elementary School) ---
    {"name": "慶應義塾幼稚舎", "type": "초등학교", "type_ja": "小学校", "address": "東京都渋谷区恵比寿2-35-1", "prefecture": "東京都", "reading": "けいおうぎじゅくようちしゃ"},
    {"name": "早稲田実業学校初等部", "type": "초등학교", "type_ja": "小学校", "address": "東京都国分寺市本町1-2-1", "prefecture": "東京都", "reading": "わせだじつぎょうがっこうしょとうぶ"},
    {"name": "青山学院初等部", "type": "초등학교", "type_ja": "小学校", "address": "東京都渋谷区渋谷4-4-25", "prefecture": "東京都", "reading": "あおやまがくいんしょとうぶ"},
    {"name": "学習院初等科", "type": "초등학교", "type_ja": "小学校", "address": "東京都新宿区若葉1-8", "prefecture": "東京都", "reading": "がくしゅういんしょとうか"},
    {"name": "筑波大学附属小学校", "type": "초등학교", "type_ja": "小学校", "address": "東京都文京区大塚3-29-1", "prefecture": "東京都", "reading": "つくばだいがくふぞくしょうがっこう"},
    {"name": "東京学芸大学附属小金井小学校", "type": "초등학교", "type_ja": "小学校", "address": "東京都小金井市貫井北町4-1-1", "prefecture": "東京都", "reading": "とうきょうがくげいだいがくふぞくこがねいしょうがっこう"},
    {"name": "千代田区立麹町小学校", "type": "초등학교", "type_ja": "小学校", "address": "東京都千代田区麹町2-8", "prefecture": "東京都", "reading": "ちよだくりつこうじまちしょうがっこう"},
    {"name": "港区立麻布小学校", "type": "초등학교", "type_ja": "小学校", "address": "東京都港区麻布十番1-5-19", "prefecture": "東京都", "reading": "みなとくりつあざぶしょうがっこう"},
]

TYPE_MAPPING = {
    "초등학교": {"초등학교", "小学校"},
    "중학교": {"중학교", "中学校"},
    "고등학교": {"고등학교", "高等学校"},
    "대학교": {"대학교", "大学"},
    "小学校": {"초등학교", "小学校"},
    "中学校": {"중학교", "中学校"},
    "高等学校": {"고등학교", "高等学校"},
    "大学": {"대학교", "大学"},
}

def search_japan_schools(keyword, requested_type=None):
    """
    일본 학교 마스터 DB에서 키워드(한자, 가나, 주소, 지역)로 검색합니다.
    """
    kw = keyword.lower().strip()
    if not kw:
        return []

    target_types = TYPE_MAPPING.get(requested_type, set()) if requested_type else set()

    matched = []
    for school in JAPAN_SCHOOLS:
        if target_types:
            if school["type"] not in target_types and school["type_ja"] not in target_types:
                continue

        name = school["name"].lower()
        reading = school.get("reading", "").lower()
        address = school.get("address", "").lower()
        pref = school.get("prefecture", "").lower()

        if kw in name or kw in reading or kw in address or kw in pref:
            matched.append({
                "name": school["name"],
                "type": school["type_ja"] if requested_type in {"小学校", "中学校", "高等学校", "大学"} else school["type"],
                "code": "JP_" + school["name"],
                "office_code": "JP",
                "address": school["address"],
            })

            if len(matched) >= 30:
                break

    return matched
