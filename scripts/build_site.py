# -*- coding: utf-8 -*-
"""우아경조사 정적 사이트 생성기 — 축의금·조의금·돌잔치 등 경조사비 기준표, 관계별 가이드, 금액 계산기, 봉투 쓰는 법.
공식 통계가 없는 분야라 금액은 2026년 설문(평균 축의금 약 9.8만원·조의금 약 9.5만원, 10만원이 최빈)과 일반 가이드를 종합한 '통용 범위'로 표기한다.
"""
import json, shutil, sys
from datetime import datetime, timedelta, timezone

from common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
TODAY = (datetime.now(timezone.utc) + timedelta(hours=9)).date()
RSLUG = {"friend": "친구", "bestfriend": "절친", "colleague": "직장동료", "acq": "타부서동료", "boss": "직장상사", "junior": "후배", "cousin": "사촌친척", "nephew": "조카", "sibling": "형제자매", "client": "거래처", "neighbor": "이웃지인"}
STEPS = [3, 5, 7, 10, 15, 20, 30, 50, 70, 100]  # 4·6은 피하는 관례를 반영한 금액 단계(만원)

SRC = [("아무튼, 주말×SM C&C 경조사비 설문(2026, 다음뉴스)", "https://v.daum.net/v/20260516003319431"),
       ("청탁금지법 시행 10주년 정리(법률신문)", "https://www.lawtimes.co.kr/news/articleView.html?idxno=228303"),
       ("청탁금지법 식사비 상향 안내(정책브리핑)", "https://m.korea.kr/news/policyNewsView.do?newsId=148932800")]

# 관계: (키, 표시, 최소선, 보통, 가까운 사이) — 단위 만원
EVENTS = {
    "wedding": dict(slug="축의금", name="결혼식 축의금", short="축의금", icon="💐", envelope=[("결혼식", "축 결혼(祝結婚) · 축 화혼(祝華婚)"), ("성당·교회 예식", "축 성혼(祝聖婚) · 축 결혼")],
                    lead="축의금은 2026년 설문에서 평균 약 9만 8천 원, 응답자의 65%가 10만 원을 낸다고 답할 만큼 10만 원이 기준선이 됐습니다. 식사를 하지 않거나 참석이 어려운 사이는 5만 원, 가까운 사이는 10~20만 원 이상으로 정리하는 경우가 많습니다.",
                    rels=[("friend", "친구", 5, 10, 15), ("bestfriend", "절친", 10, 20, 30), ("colleague", "직장 동료(같은 팀)", 5, 10, 10), ("acq", "타 부서·안면 있는 동료", 3, 5, 7),
                          ("boss", "직장 상사", 5, 10, 10), ("junior", "부하·후배", 5, 10, 10), ("cousin", "사촌·친척", 10, 10, 30), ("nephew", "조카", 30, 50, 100),
                          ("sibling", "형제·자매", 30, 50, 100), ("client", "거래처·업무상 지인", 5, 5, 10), ("neighbor", "이웃·지인", 3, 5, 10)]),
    "funeral": dict(slug="조의금", name="장례식 조의금", short="조의금", icon="🕊️", envelope=[("일반", "부의(賻儀) · 근조(謹弔) · 조의(弔意)"), ("종교에 맞출 때", "기독교는 추모·근조, 불교는 부의·근조 등으로 쓰며, 종교를 모르면 '부의'나 '근조'가 무난합니다.")],
                    lead="조의금도 2026년 설문에서 평균 약 9만 5천 원, 10만 원이 가장 많은 응답이었습니다. 다만 직장 동료·지인은 5만 원, 가까운 친구·친척은 10만 원 이상으로 나누는 곳이 많고, 조부모상은 부모상보다 낮게 잡는 편입니다.",
                    rels=[("colleague", "직장 동료", 5, 5, 10), ("boss", "직장 상사", 5, 10, 10), ("junior", "부하·후배", 5, 5, 10), ("friend", "친구", 5, 10, 10), ("bestfriend", "절친", 10, 10, 20),
                          ("cousin", "사촌·친척", 10, 10, 30), ("neighbor", "이웃·지인", 3, 5, 5), ("client", "거래처·업무상 지인", 5, 5, 10)]),
    "dol": dict(slug="돌잔치", name="돌잔치 축하금", short="돌잔치", icon="🎂", envelope=[("돌잔치", "축 돌(祝 돌) · 축 첫돌")],
                lead="돌잔치는 식사를 대접받는 자리라 식대를 고려해 5~10만 원, 가까운 사이는 10만 원 이상 또는 돌반지·선물로 마음을 전하는 경우가 많습니다.",
                rels=[("friend", "친구·지인", 5, 5, 10), ("colleague", "직장 동료", 3, 5, 5), ("cousin", "친척", 5, 10, 20), ("sibling", "형제·자매", 10, 20, 30)]),
    "housewarming": dict(slug="집들이", name="집들이 선물·축하금", short="집들이", icon="🏠", envelope=[("집들이", "축 입주(祝入住) · 축 집들이")],
                         lead="집들이는 현금보다 선물(휴지·세제·디퓨저·주방용품 등 3~5만 원대)을 가져가는 경우가 많고, 현금은 5~10만 원 선입니다.",
                         rels=[("friend", "친구·지인", 3, 5, 10), ("colleague", "직장 동료", 3, 5, 5), ("cousin", "친척", 5, 10, 20), ("sibling", "형제·자매", 10, 20, 30)]),
    "birth": dict(slug="출산축하", name="출산·병문안 축하금", short="출산축하", icon="👶", envelope=[("출산 축하", "축 순산(祝順産) · 축 출산(祝出産)"), ("병문안", "쾌유를 빕니다(快癒) · 위문")],
                  lead="출산 축하금은 5~10만 원, 가까운 사이는 10~20만 원이 일반적입니다. 병문안은 3~5만 원 상당의 음료·과일·봉투로 대신하기도 합니다.",
                  rels=[("friend", "친구·지인", 5, 10, 10), ("colleague", "직장 동료", 3, 5, 10), ("cousin", "친척", 5, 10, 20), ("sibling", "형제·자매", 10, 20, 30)]),
    "opening": dict(slug="개업축하", name="개업·개원 축하금", short="개업축하", icon="🎉", envelope=[("개업·개원", "축 개업(祝開業) · 축 발전(祝發展) · 축 번영(祝繁榮)")],
                    lead="개업 축하는 현금 5~10만 원 또는 같은 금액대의 화환·화분이 일반적이며, 가까운 사이는 10만 원 이상을 전하기도 합니다. 공직자 등에게는 청탁금지법 상한을 확인하세요.",
                    rels=[("friend", "친구·지인", 5, 10, 10), ("colleague", "직장 동료", 5, 5, 10), ("cousin", "친척", 5, 10, 20), ("client", "거래처", 5, 10, 10)]),
    "promotion": dict(slug="승진축하", name="승진·취임 축하금", short="승진축하", icon="🏅", envelope=[("승진·취임", "축 승진(祝昇進) · 축 영전(祝榮轉) · 축 취임(祝就任)")],
                      lead="승진·취임 축하는 부서 회식이나 선물로 대신하는 경우가 많고, 현금은 5~10만 원 선입니다. 직장 내에서는 청탁금지법·사내 규정을 먼저 확인하세요.",
                      rels=[("colleague", "직장 동료", 3, 5, 5), ("boss", "직장 상사", 5, 5, 10), ("junior", "부하·후배", 5, 5, 10), ("friend", "친구·지인", 5, 5, 10)]),
    "hwangap": dict(slug="환갑칠순", name="환갑·칠순 축하금", short="환갑칠순", icon="🎊", envelope=[("환갑", "축 수연(祝壽宴) · 축 회갑(祝回甲)"), ("칠순", "축 칠순(祝七旬) · 축 고희(祝古稀)")],
                    lead="환갑·칠순은 잔치 대신 가족 식사로 대신하는 경우가 늘었습니다. 잔치에 초대받았다면 5~10만 원, 친척·가까운 사이는 10만 원 이상이 일반적입니다.",
                    rels=[("friend", "지인·이웃", 5, 5, 10), ("cousin", "친척", 10, 10, 30), ("nephew", "조카", 10, 20, 30), ("sibling", "형제·자매", 20, 30, 50)]),
    "graduation": dict(slug="입학졸업", name="입학·졸업 축하금", short="입학졸업", icon="🎓", envelope=[("졸업", "축 졸업(祝卒業)"), ("입학", "축 입학(祝入學)")],
                       lead="입학·졸업 축하금은 학년과 관계에 따라 다르며, 조카에게는 초등 3~5만 원, 중·고등 5~10만 원, 대학 입학·졸업 10~20만 원 정도로 정리하는 경우가 많습니다.",
                       rels=[("friend", "친구·지인 자녀", 3, 5, 10), ("cousin", "친척 자녀", 5, 10, 20), ("nephew", "조카", 5, 10, 30), ("sibling", "형제·자매", 10, 20, 30)]),
}
ORDER = ["wedding", "funeral", "dol", "housewarming", "birth", "opening", "promotion", "hwangap", "graduation"]

# 관계별 안내 — (경조사, 관계) → (소개, [팁 3개], [(질문, 답)] 2개)
RT = {
    ("wedding", "friend"): ("친구 결혼식은 서로의 결혼식에 오가는 사이라 '받은 만큼 돌려준다'는 기준이 가장 많이 쓰입니다.",
                            ["식사를 하고 오는 예식이면 10만 원, 호텔·고급 예식장이면 15만 원까지 올리는 경우가 많습니다.", "참석하지 못해 계좌로 보낼 때는 같은 금액이나 한 단계 낮게(예: 10→5만 원) 보내는 경우가 많습니다.", "내 결혼식에 상대가 낸 금액이 있다면 그 금액 이상으로 맞추는 것이 관례입니다."],
                            [("친구 결혼식 축의금은 5만 원도 괜찮나요?", "식사 없이 인사만 하거나 연락이 뜸한 사이라면 5만 원도 흔합니다. 다만 요즘은 식사를 한다면 10만 원이 기준선이라는 응답이 많습니다."), ("친구 결혼식에 부부가 같이 가면 얼마를 내나요?", "둘이 함께 식사한다면 보통 10만 원 이상, 가까운 사이면 15~20만 원을 내는 경우가 많습니다.")]),
    ("wedding", "bestfriend"): ("절친은 오랜 시간 함께한 사이라 금액을 높게 잡고, 결혼 준비를 돕거나 축가·사회를 맡는 경우도 있습니다.",
                                ["20만 원이 중심이고 아주 가까우면 30만 원 이상도 합니다.", "도우미·사회·축가를 맡았다면 축의금과 별개로 감사 선물을 챙기는 경우가 많습니다.", "서로 비슷한 시기에 결혼한다면 미리 기준을 맞춰 두면 서운함이 줄어듭니다."],
                                [("절친 축의금 30만 원은 많은 건가요?", "친한 사이에서는 흔한 금액입니다. 형편과 서로 주고받은 이력을 함께 고려하세요."), ("절친 결혼식에 현금 외에 선물도 해야 하나요?", "필수는 아니지만 신혼집에 필요한 선물이나 상품권을 따로 전하기도 합니다.")]),
    ("wedding", "colleague"): ("같은 팀 동료는 매일 보는 사이라 너무 적으면 어색하고, 너무 많으면 부담이 되니 팀 분위기를 참고하는 것이 좋습니다.",
                               ["팀 전체가 같은 금액을 맞추는 경우가 많으니 선배에게 팀 관행을 먼저 물어보세요.", "식사를 하고 오면 10만 원, 식사 없이 축하만 하면 5만 원도 많이 합니다.", "친한 동료가 아니면 팀 회비(공동 축의금)로 대신하기도 합니다."],
                               [("직장 동료 결혼식 축의금 5만 원이면 부족한가요?", "식사 없이 인사만 한다면 괜찮지만, 식사를 한다면 10만 원이 기준이라는 의견이 많습니다."), ("퇴사한 동료의 결혼식에도 가야 하나요?", "관계에 따라 다릅니다. 연락을 이어 온 사이라면 축하와 함께 5~10만 원을 보내는 경우가 많습니다.")]),
    ("wedding", "acq"): ("타 부서나 얼굴만 아는 동료는 예의를 갖추되 부담 없는 선에서 맞추면 됩니다.",
                         ["참석하지 않고 축하 메시지와 3~5만 원을 전하는 경우가 많습니다.", "식사를 한다면 5만 원이 최소선입니다.", "청첩장을 받았다면 직접 인사하고 금액은 팀 분위기를 따르세요."],
                         [("얼굴만 아는 사이인데 청첩장을 받았어요. 얼마를 낼까요?", "참석하면 5만 원, 불참하면 3~5만 원을 계좌로 보내는 경우가 많습니다."), ("청첩장을 받고도 안 가면 실례인가요?", "일정이 어렵다면 미리 축하 메시지와 함께 소액을 보내면 무난합니다.")]),
    ("wedding", "boss"): ("직장 상사는 금액보다 예의가 중요한 관계라 10만 원 안팎이 무난하고 지나치게 큰 금액은 오히려 부담이 될 수 있습니다.",
                          ["5~10만 원이 일반적이며 팀에서 함께 내는 경우도 있습니다.", "공공기관·공직자는 청탁금지법 상한(5만 원)이 있을 수 있어 확인이 필요합니다.", "축하 메시지를 함께 전하면 금액보다 좋은 인상을 줍니다."],
                          [("상사 결혼식 축의금을 팀원이 모아서 내도 되나요?", "팀 관행이 있다면 모아서 내기도 합니다. 개인 금액은 5만 원 안팎으로 맞추는 경우가 많습니다."), ("상사에게 너무 적게 내면 눈치가 보일까요?", "과하지 않게 팀 기준에 맞추면 충분합니다.")]),
    ("wedding", "junior"): ("후배·부하는 부담을 주지 않는 선에서 축하하되, 가까운 후배라면 조금 더 챙겨 주는 것이 좋습니다.",
                            ["10만 원이 일반적이고 가까운 후배는 그 이상을 하기도 합니다.", "후배가 먼저 내 경조사에 참석했다면 그 이상으로 맞추세요.", "팀장이라면 팀 전체 공동 축의금을 제안해도 됩니다."],
                            [("후배 결혼식에는 얼마를 하면 좋을까요?", "10만 원이 많이 쓰이고, 아주 가깝다면 15~20만 원도 합니다."), ("후배에게 받은 금액이 적으면 어떻게 하죠?", "받은 금액과 상관없이 현재 관계를 기준으로 하되, 보통 받은 금액 이상으로 맞춥니다.")]),
    ("wedding", "cousin"): ("사촌·친척은 평소 왕래 정도에 따라 크게 달라지며, 가까운 사촌은 10~30만 원 사이에서 결정합니다.",
                            ["왕래가 적은 사촌은 10만 원, 자주 만나는 사촌은 20~30만 원 정도로 많이 합니다.", "집안 분위기나 부모님 의견을 참고하세요.", "서로 주고받은 기록(경조사 장부)이 있다면 그에 맞추면 편합니다."],
                            [("사촌 결혼식 축의금은 얼마가 적당한가요?", "10만 원이 기본이고 가까우면 20~30만 원입니다. 부모님과 상의해 정하는 경우가 많습니다."), ("친척 결혼식은 부부가 함께 가면 더 내야 하나요?", "부부가 함께 식사하면 보통 한 단계 높게(예: 10→20만 원) 냅니다.")]),
    ("wedding", "nephew"): ("조카는 가족이라 금액 폭이 크고, 친조카와 사촌 조카의 기준이 다르게 쓰입니다.",
                            ["친조카는 50~100만 원, 사촌 조카는 30~50만 원이라는 안내가 많이 쓰입니다.", "형제자매와 의논해 비슷한 금액으로 맞추면 갈등이 없습니다.", "큰 금액이라 부담이면 축의금과 선물을 나눠 전하기도 합니다."],
                            [("조카 결혼식에 100만 원은 너무 많은가요?", "친조카라면 흔한 금액이지만 형편에 맞추는 것이 가장 중요합니다."), ("외삼촌·이모 쪽 조카도 같은 기준인가요?", "가까운 사이라면 같은 기준으로 하는 경우가 많습니다.")]),
    ("wedding", "sibling"): ("형제·자매는 가족 행사라 금액을 크게 잡는 경우가 많고, 부모님과 함께 준비하는 경우도 있습니다.",
                             ["30~100만 원으로 폭이 넓으며 형편에 맞추는 것이 가장 중요합니다.", "축의금 외에 혼수 일부나 선물을 따로 챙기기도 합니다.", "형제가 여럿이라면 서로 금액을 맞춰 두세요."],
                             [("형제 결혼식 축의금 평균은 얼마인가요?", "공식 통계는 없지만 50만 원 안팎이 많이 인용됩니다. 상황에 따라 100만 원 이상도 있습니다."), ("남매 사이에서도 금액을 맞추나요?", "형제자매끼리는 비슷한 수준으로 맞추는 경우가 많습니다.")]),
    ("wedding", "client"): ("거래처는 관계 유지가 목적이므로 과하지 않고 부담 없는 5~10만 원이 일반적입니다.",
                            ["직접 참석이 어려우면 화환이나 계좌이체로 대신합니다.", "상대가 공직자·공공기관이면 청탁금지법 상한을 확인하세요.", "영수증·내부 규정이 필요한 회사는 사전에 확인하세요."],
                            [("거래처 결혼식에 화환을 보내도 되나요?", "축의금 대신 화환(5~10만 원대)을 보내는 경우가 많습니다. 예식장이 화환을 받는지 확인하세요."), ("거래처 청첩장을 받으면 꼭 참석해야 하나요?", "관계 정도에 따라 참석하거나 축의금만 전합니다.")]),
    ("wedding", "neighbor"): ("이웃·지인은 얼굴을 아는 사이라면 3~5만 원으로 마음을 전하는 경우가 많습니다.",
                              ["식사를 한다면 5만 원 이상이 일반적입니다.", "지역 관행이 있다면 따르세요.", "참석이 어려우면 축하 인사와 소액을 전합니다."],
                              [("이웃 자녀의 결혼식에는 얼마를 내나요?", "5만 원 안팎이 많이 쓰입니다."), ("청첩장 없이 소식만 들었다면 어떻게 하나요?", "직접 초대받지 않았다면 축하 인사만 전해도 충분합니다.")]),
    ("funeral", "colleague"): ("직장 동료 조의는 팀 단위로 모아 내는 경우가 많고, 직접 낼 때는 5만 원이 무난한 기준으로 자리 잡았습니다.",
                               ["동료 본인상·부모상은 5만 원이 많고, 가까운 사이는 10만 원도 합니다.", "조부모·외조부모상은 3~5만 원으로 낮게 잡는 경우가 많습니다.", "회사에서 조의금(경조비)을 별도로 지급하는지 확인하세요."],
                               [("직장 동료 부모상 조의금 5만 원이면 되나요?", "가장 흔한 금액입니다. 친한 사이면 10만 원도 합니다."), ("장례식장에 직접 가야 하나요?", "가까운 사이면 직접 조문하고, 어려우면 계좌이체와 조문 메시지로 대신하기도 합니다.")]),
    ("funeral", "boss"): ("상사 조의는 예의를 갖춰야 하는 자리이므로 5~10만 원 범위에서 팀 기준을 따르세요.",
                          ["팀원 모두가 함께 조의금을 모아 전하는 경우도 있습니다.", "직접 조문이 어렵다면 조화·조전을 이용하기도 합니다.", "공직자는 청탁금지법 상한(5만 원, 조화 10만 원)이 있을 수 있어 확인하세요."],
                          [("상사 부모상 조의금은 얼마가 좋을까요?", "5~10만 원이 무난하고 팀 관행에 맞추세요."), ("상사 본인상일 때는 더 많이 내야 하나요?", "관계에 따라 같은 수준이거나 조금 높이는 경우가 있습니다.")]),
    ("funeral", "junior"): ("후배·부하에게는 마음을 전하는 선에서 5~10만 원을 내는 경우가 많습니다.",
                            ["가까운 후배라면 10만 원 이상도 합니다.", "직접 조문하는 것이 금액보다 큰 위로가 됩니다.", "팀 이름으로 조화를 함께 보내기도 합니다."],
                            [("후배 부모상에 얼마를 낼까요?", "5만 원이 흔하고 가까우면 10만 원입니다."), ("팀원 모두 같은 금액을 내야 하나요?", "맞추는 경우가 많지만 필수는 아닙니다.")]),
    ("funeral", "friend"): ("친구는 부모상에서 서로 오가는 사이라 10만 원이 기준선으로 자리 잡는 추세입니다.",
                            ["10만 원이 가장 많고, 연락이 뜸했던 사이는 5만 원도 합니다.", "친구 본인상은 더 크게 챙기는 경우가 많습니다.", "친구 부모님의 조문은 직접 방문이 가장 큰 위로입니다."],
                            [("친구 부모상 조의금 5만 원은 적은가요?", "사이가 가깝지 않다면 괜찮지만 요즘은 10만 원이 기준이라는 응답이 많습니다."), ("친구 조부모상에도 조의금을 내나요?", "가까운 사이라면 5만 원 안팎으로 전하는 경우가 많습니다.")]),
    ("funeral", "bestfriend"): ("절친은 장례 기간 동안 곁을 지켜 주는 것도 중요하고, 금액은 10~20만 원으로 정리하는 경우가 많습니다.",
                                ["10만 원 이상이 일반적이며 가까울수록 높입니다.", "일손을 도울 수 있다면 금액과 별개로 큰 도움이 됩니다.", "상황을 보고 장례 후에도 안부를 챙기세요."],
                                [("절친 부모상에는 얼마를 내야 하나요?", "10~20만 원이 많이 쓰입니다."), ("장례식장에서 얼마나 머물러야 하나요?", "조문과 식사를 마치고 가는 경우가 많고, 가까운 사이는 늦게까지 머물기도 합니다.")]),
    ("funeral", "cousin"): ("친척 조의는 가까움에 따라 10~30만 원이며, 집안 관례를 따르는 경우가 많습니다.",
                            ["왕래가 잦은 친척은 20~30만 원, 먼 친척은 10만 원 정도입니다.", "부모님과 상의해 금액을 맞추세요.", "상주를 돕는 일손이 필요한 경우가 많습니다."],
                            [("외가·친가 친척 조의금은 같은 기준인가요?", "가까운 정도에 따라 다르며 보통 비슷한 수준으로 합니다."), ("친척이 많은데 금액을 어떻게 정하나요?", "집안 어른이나 부모님의 기준을 따르는 것이 가장 무난합니다.")]),
    ("funeral", "neighbor"): ("이웃·지인은 마음을 전하는 선에서 3~5만 원을 내는 경우가 많습니다.",
                              ["관계가 얕다면 3만 원도 무난합니다.", "직접 방문이 어렵다면 안부 인사와 소액 이체를 합니다.", "지역 관행이 있다면 따르세요."],
                              [("이웃 상가에 조의금은 얼마가 적당한가요?", "3~5만 원이 흔합니다."), ("모르는 분의 상가에도 가야 하나요?", "이웃 간 관례가 있다면 따르되 필수는 아닙니다.")]),
    ("funeral", "client"): ("거래처 조의는 관계 유지 차원에서 5~10만 원 정도가 일반적입니다.",
                            ["직접 조문 또는 조화·조전으로 마음을 전합니다.", "상대가 공직자·공공기관이면 청탁금지법 상한을 확인하세요.", "회사 규정이 있다면 따르세요."],
                            [("거래처 상가에 조화를 보내도 되나요?", "조화(5~10만 원대)를 보내는 경우가 많습니다."), ("직접 조문하지 못하면 어떻게 하나요?", "조전·조화 또는 계좌이체와 함께 위로 메시지를 전합니다.")]),
}


def step_down(v):
    i = STEPS.index(min(STEPS, key=lambda s: abs(s - v)))
    return STEPS[max(0, i - 1)]


def tbl(rows):
    return '<div class="tbl-wrap"><table class="tbl"><tr><th>관계</th><th>최소선</th><th>많이 하는 금액</th><th>가까운 사이</th></tr>%s</table></div>' % "".join(
        "<tr><td>%s</td><td>%s만 원</td><td><b>%s만 원</b></td><td>%s만 원</td></tr>" % (esc(l), a, b, c) for _, l, a, b, c in rows)


def src_html():
    return '<h2 class="group-title">참고 자료</h2><ul class="lead">%s</ul><p class="note">경조사비에는 공식 통계가 없어 위 설문·정리 자료와 일반 가이드를 종합한 통용 범위입니다. 블로그·가이드마다 기준이 다르므로 지역·관계·형편에 맞춰 조정하세요.</p>' % "".join(
        '<li><a href="%s" rel="nofollow noopener" target="_blank">%s</a></li>' % (u, esc(t)) for t, u in SRC)


def calc_script():
    data = {e: {k: [a, b, c] for k, _, a, b, c in v["rels"]} for e, v in EVENTS.items()}
    labels = {e: {k: l for k, l, *_ in v["rels"]} for e, v in EVENTS.items()}
    names = {e: v["name"] for e, v in EVENTS.items()}
    return ("<script>var D=%s,L=%s,N=%s,S=%s;" % (json.dumps(data, ensure_ascii=False), json.dumps(labels, ensure_ascii=False), json.dumps(names, ensure_ascii=False), json.dumps(STEPS)) + """
(function(){var ev=document.getElementById('c-ev'),rel=document.getElementById('c-rel'),cl=document.getElementById('c-close'),mm=document.getElementById('c-meal'),ho=document.getElementById('c-hotel'),rc=document.getElementById('c-recv'),out=document.getElementById('c-out'),mw=document.getElementById('c-wedrow');
function near(v){var b=S[0];for(var i=0;i<S.length;i++){if(Math.abs(S[i]-v)<Math.abs(b-v))b=S[i];}return b;}
function up(v){for(var i=0;i<S.length;i++){if(S[i]>v)return S[i];}return v;}
function down(v){var p=S[0];for(var i=0;i<S.length;i++){if(S[i]<v)p=S[i];}return p;}
function fillRel(){rel.innerHTML='';var k=D[ev.value];for(var r in k){var o=document.createElement('option');o.value=r;o.textContent=L[ev.value][r];rel.appendChild(o);}mw.style.display=ev.value==='wedding'?'':'none';calc();}
function calc(){var d=D[ev.value][rel.value];if(!d)return;var base=cl.value==='low'?d[0]:cl.value==='high'?d[2]:d[1];var note=[];
if(ev.value==='wedding'){if(mm.value==='no'){var nb=cl.value==='high'?d[1]:d[0];if(nb!==base){note.push('식사를 하지 않거나 불참해 최소선 기준으로 낮췄습니다.');}base=nb;}if(ho.value==='yes'){base=up(base);note.push('호텔·고급 예식이라 한 단계 올렸습니다.');}}
var rec=near(base);var rv=parseFloat(rc.value);if(rv>0&&rv>rec){rec=near(rv);note.push('받은 금액('+rv+'만 원) 이상으로 맞췄습니다.');}
var lo=Math.min(d[0],rec),hi=Math.max(d[2],rec);
out.innerHTML='<div class="result-main" style="font-size:2rem;font-weight:800;color:var(--primary)">'+rec+'만 원</div><p class="lead">'+L[ev.value][rel.value]+' '+N[ev.value]+' 추천 금액입니다. 통용 범위는 '+d[0]+'~'+d[2]+'만 원입니다.</p>'+(note.length?'<ul class="lead"><li>'+note.join('</li><li>')+'</li></ul>':'')+'<p class="note">4만 원·6만 원은 피하는 관례를 반영했습니다. 참고용이며 형편과 관계에 맞춰 조정하세요.</p>';}
[ev,rel,cl,mm,ho].forEach(function(e){e.addEventListener('change',calc)});rc.addEventListener('input',calc);ev.addEventListener('change',fillRel);fillRel();})();
</script>""")


def calc_html():
    ev = "".join('<option value="%s">%s</option>' % (e, EVENTS[e]["name"]) for e in ORDER)
    return ('<div class="panel" style="padding:18px;border:1px solid #E5E7EB;border-radius:12px;background:#fff"><h2 class="group-title" style="margin-top:0">경조사비 금액 계산기</h2>'
            '<div class="calc-grid" style="display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr))">'
            '<label>경조사<select id="c-ev" style="width:100%%;padding:8px">%s</select></label>'
            '<label>관계<select id="c-rel" style="width:100%%;padding:8px"></select></label>'
            '<label>친밀도<select id="c-close" style="width:100%%;padding:8px"><option value="low">보통 이하 (연락 드문 사이)</option><option value="mid" selected>보통</option><option value="high">가까운 사이</option></select></label>'
            '<label id="c-wedrow">식사 여부<select id="c-meal" style="width:100%%;padding:8px"><option value="yes">참석해서 식사</option><option value="no">식사 안 함/불참(계좌이체)</option></select>'
            '<select id="c-hotel" style="width:100%%;padding:8px;margin-top:6px"><option value="no">일반 예식장</option><option value="yes">호텔·고급 예식</option></select></label>'
            '<label>상대가 내게 낸 금액(선택, 만 원)<input id="c-recv" type="number" min="0" step="1" style="width:100%%;padding:8px" placeholder="예: 10"></label></div>'
            '<div id="c-out" style="margin-top:14px"></div></div>' % ev) + calc_script()


def page_event(e, v):
    rows = v["rels"]
    body = ['<div class="page-head"><h1>%s 얼마가 적당할까?</h1><p>%s 관계별 기준표</p></div>' % (esc(v["name"]), esc(v["short"])), '<p class="lead">%s</p>' % esc(v["lead"]), ad(), tbl(rows)]
    links = []
    for k, l, *_ in rows:
        if (e, k) in RT:
            links.append('<a class="chip" href="/%s/%s/">%s %s</a>' % (q(v["slug"]), q(RSLUG[k]), esc(l), esc(v["short"])))
    if links:
        body.append('<h2 class="group-title">관계별 자세한 기준</h2><div class="chips">%s</div>' % "".join(links))
    body.append('<h2 class="group-title">봉투 앞면 문구</h2><div class="tbl-wrap"><table class="tbl">%s</table></div>' % "".join("<tr><th>%s</th><td>%s</td></tr>" % (esc(a), esc(b)) for a, b in v["envelope"]))
    body.append('<p><a class="btn" href="/계산기/">🧮 내 상황에 맞는 금액 계산하기</a></p>')
    if e == "funeral":
        body.append('<p class="note">장례식장 위치는 <a href="https://wooafuneral.wooahouse.com">우아장례</a>에서 찾을 수 있습니다.</p>')
    body.append('<h2 class="group-title">공통 매너 체크</h2><ul class="lead"><li>4만 원·6만 원은 피하고 3·5·7·10만 원 같은 금액을 쓰는 관례가 있습니다.</li><li>이름은 봉투 뒷면 왼쪽 아래에 적는 것이 일반적입니다.</li><li>상대가 나에게 낸 금액이 있다면 그 금액 이상으로 맞추는 것이 관례입니다.</li><li>공직자 등에게는 청탁금지법 상한(경조사비 5만 원, 화환·조화 10만 원)이 있을 수 있습니다. <a href="/청탁금지법/">자세히</a></li></ul>')
    body.append(src_html())
    faq = [("%s 기본 금액은 얼마인가요?" % v["name"], "공식 기준은 없고, 관계와 친밀도에 따라 다릅니다. 이 페이지의 표에서 관계별 통용 범위를 확인하세요."),
           ("%s는 홀수로 내야 하나요?" % v["short"], "예전부터 짝수를 피하는 관례가 있어 3·5·7만 원을 쓰지만 10만 원은 일반적으로 쓰입니다. 4만 원·6만 원은 피하는 경우가 많습니다.")]
    write("/%s/" % v["slug"], layout("/%s/" % v["slug"], "%s 얼마? 관계별 기준표 2026" % v["name"], "%s 관계별 통용 금액과 봉투 문구, 매너를 2026년 설문 기준으로 정리했습니다." % v["name"], "\n".join(body), faq,
                                      [("홈", "/"), (v["short"], "/%s/" % v["slug"])], coupang=True), "0.9")
    for k, l, a, b, c in rows:
        if (e, k) not in RT:
            continue
        intro, tips, qa = RT[(e, k)]
        path = "/%s/%s/" % (v["slug"], RSLUG[k])
        bd = ['<div class="page-head"><h1>%s %s 얼마?</h1><p>2026년 기준 통용 범위</p></div>' % (esc(l), esc(v["short"])), '<p class="lead">%s <b>많이 하는 금액은 %s만 원</b>(최소선 %s만 원, 가까운 사이 %s만 원)입니다.</p>' % (esc(intro), b, a, c), ad(),
              '<div class="tbl-wrap"><table class="tbl"><tr><th>상황</th><th>금액</th></tr><tr><td>연락이 드문 사이·식사 없이 인사만</td><td>%s만 원</td></tr><tr><td>보통 사이</td><td><b>%s만 원</b></td></tr><tr><td>가까운 사이</td><td>%s만 원 이상</td></tr></table></div>' % (a, b, c),
              '<h2 class="group-title">이럴 땐 이렇게</h2><ul class="lead">%s</ul>' % "".join("<li>%s</li>" % esc(t) for t in tips),
              '<p><a class="btn" href="/계산기/">🧮 내 상황에 맞춰 계산하기</a></p>']
        others = [o for o in rows if o[0] != k and (e, o[0]) in RT][:6]
        bd.append('<h2 class="group-title">다른 관계 %s</h2><div class="chips">%s</div>' % (esc(v["short"]), "".join('<a class="chip" href="/%s/%s/">%s</a>' % (q(v["slug"]), q(RSLUG[o[0]]), esc(o[1])) for o in others)))
        bd.append('<h2 class="group-title">같은 관계 다른 경조사</h2><div class="chips">%s</div>' % "".join(
            '<a class="chip" href="/%s/%s/">%s %s</a>' % (q(EVENTS[o]["slug"]), q(RSLUG[k]), esc(l), esc(EVENTS[o]["short"])) for o in ("wedding", "funeral") if o != e and (o, k) in RT))
        bd.append(src_html())
        write(path, layout(path, "%s %s 얼마? 2026 기준 %s만 원" % (l, v["short"], b), "%s %s는 보통 %s만 원(범위 %s~%s만 원)입니다. 관계별 팁과 봉투 문구를 정리했습니다." % (l, v["short"], b, a, c), "\n".join(bd), qa,
                                [("홈", "/"), (v["short"], "/%s/" % v["slug"]), (l, path)], coupang=True), "0.8")


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    for ch in OUT.iterdir():
        shutil.rmtree(ch) if ch.is_dir() else ch.unlink()
    for e in ORDER:
        page_event(e, EVENTS[e])
    # 계산기
    write("/계산기/", layout("/계산기/", "경조사비 금액 계산기 - 축의금·조의금 얼마?", "경조사·관계·친밀도·식사 여부를 고르면 축의금·조의금 추천 금액을 계산해 드립니다.",
                           '<div class="page-head"><h1>경조사비 금액 계산기</h1><p>관계와 상황에 맞는 금액 추천</p></div>' + calc_html() + ad() + src_html(), None, [("홈", "/"), ("금액 계산기", "/계산기/")]), "0.9")
    # 봉투
    rows = [(v["name"], a, b) for e in ORDER for v in [EVENTS[e]] for a, b in v["envelope"]]
    body = ['<div class="page-head"><h1>경조사 봉투 쓰는 법</h1><p>앞면 문구와 이름 쓰는 위치</p></div>', ad(),
            '<h2 class="group-title">경조사별 앞면 문구</h2><div class="tbl-wrap"><table class="tbl"><tr><th>경조사</th><th>상황</th><th>문구</th></tr>%s</table></div>' % "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(a), esc(b), esc(c)) for a, b, c in rows),
            '<h2 class="group-title">이름은 어디에 쓰나요?</h2><ul class="lead"><li>이름은 봉투 <b>뒷면 왼쪽 아래</b>에 쓰는 것이 일반적입니다. 회사 이름을 함께 적기도 합니다.</li><li>금액을 적을 때는 봉투 안 별지나 뒷면에 적는 경우가 있으며, 필수는 아닙니다.</li><li>지폐는 깨끗한 새 지폐를 펴서 넣고, 인물이 위로 오게 넣는 것이 관례입니다.</li></ul>',
            '<div class="note-box">한자 대신 한글(축 결혼, 부의 등)로 써도 예의에 어긋나지 않습니다. 종교·집안에 따라 문구가 다를 수 있으니 어른께 확인하세요.</div>']
    write("/봉투/", layout("/봉투/", "경조사 봉투 쓰는 법 - 축의금·부의금 봉투 문구", "축의금·부의금·돌잔치 등 경조사별 봉투 앞면 문구와 이름 쓰는 위치를 정리했습니다.", "\n".join(body), None, [("홈", "/"), ("봉투 쓰는 법", "/봉투/")], coupang=True), "0.8")
    # 청탁금지법
    body = ['<div class="page-head"><h1>청탁금지법 경조사비 상한</h1><p>공직자 등에게 줄 때 확인할 기준</p></div>', ad(),
            '<p class="lead">청탁금지법(부정청탁 및 금품등 수수의 금지에 관한 법률)은 공직자 등에게 주는 경조사비에 상한을 둡니다. 시행령 기준으로 <b>축의금·조의금은 5만 원, 이를 대신하는 화환·조화는 10만 원</b>이며, 식사 상한은 2024년 8월 27일 3만 원에서 5만 원으로 올랐습니다.</p>',
            '<div class="tbl-wrap"><table class="tbl"><tr><th>구분</th><th>상한</th></tr><tr><td>축의금·조의금(현금)</td><td>5만 원</td></tr><tr><td>화환·조화(축의금 대신)</td><td>10만 원</td></tr><tr><td>음식물(식사)</td><td>5만 원 (2024.8.27 상향)</td></tr></table></div>',
            '<ul class="lead"><li>적용 대상은 공직자, 공공기관 임직원, 교직원, 언론인 등입니다. 같은 직장 동료 간 사적인 경조사에는 다르게 적용될 수 있습니다.</li><li>법과 시행령은 바뀔 수 있으므로 중요한 경우 국가법령정보센터나 소속 기관의 청렴 담당에게 확인하세요.</li></ul>', src_html()]
    write("/청탁금지법/", layout("/청탁금지법/", "청탁금지법 경조사비 상한 - 축의금·조의금 5만원, 화환 10만원", "청탁금지법 시행령의 경조사비 상한(축의금·조의금 5만 원, 화환·조화 10만 원)과 식사 상한을 정리했습니다.", "\n".join(body), None, [("홈", "/"), ("청탁금지법", "/청탁금지법/")]), "0.7")
    # 홈
    cards = "".join('<a class="card" href="/%s/"><b>%s %s</b><span>%s</span></a>' % (q(EVENTS[e]["slug"]), EVENTS[e]["icon"], esc(EVENTS[e]["short"]), esc(EVENTS[e]["name"])) for e in ORDER)
    wrows = EVENTS["wedding"]["rels"]
    faq = [("축의금은 얼마가 적당한가요?", "2026년 설문에서 축의금 평균은 약 9만 8천 원이고 10만 원이 가장 많았습니다. 식사를 하지 않거나 멀어진 사이는 5만 원, 가까운 사이는 10~20만 원이 일반적입니다."),
           ("조의금은 얼마가 적당한가요?", "평균 약 9만 5천 원, 10만 원이 가장 많은 응답이었습니다. 직장 동료·지인은 5만 원, 친구·친척은 10만 원 이상으로 나누는 경우가 많습니다."),
           ("경조사비에 공식 기준이 있나요?", "공식 기준은 없습니다. 이 사이트는 설문과 일반 가이드를 종합한 통용 범위를 보여주며, 지역·관계·형편에 따라 조정하세요.")]
    body = ['<div class="hero"><h1>축의금·조의금 얼마?</h1><p>관계별 기준표와 금액 계산기 — 2026년 설문 기준</p></div>', calc_html(), ad(),
            '<h2 class="group-title">경조사별 기준</h2><div class="card-grid">%s</div>' % cards,
            '<h2 class="group-title">결혼식 축의금 한눈에</h2>', tbl(wrows),
            '<p class="note">자세한 관계별 안내는 <a href="/축의금/">축의금</a>, <a href="/조의금/">조의금</a> 페이지에서 확인하세요. 봉투는 <a href="/봉투/">봉투 쓰는 법</a>, 공직자 상한은 <a href="/청탁금지법/">청탁금지법</a>을 참고하세요.</p>', src_html()]
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "우아경조사", "url": BASE + "/"}]
    write("/", layout("/", "축의금·조의금 얼마? 관계별 기준표·계산기 2026 | 우아경조사", "축의금·조의금·돌잔치·집들이·개업 축하금을 관계별 기준표와 계산기로 확인하세요. 2026년 설문 기준 통용 범위.", "\n".join(body), faq, None, "website", ld, coupang=True), "1.0")
    pages_static()
    finish()


def pages_static():
    body = ['<div class="page-head"><h1>데이터 설명</h1></div>', '<p class="lead">우아경조사는 경조사비에 대한 <b>공식 통계가 없는</b> 점을 감안해, 2026년 경조사비 설문(평균 축의금 약 9.8만 원·조의금 약 9.5만 원, 10만 원 최빈)과 청탁금지법 시행령 기준, 일반 가이드를 종합한 통용 범위를 보여줍니다. 관계별 표의 최소선·보통·가까운 사이 값은 이 자료들을 바탕으로 한 참고값이며, 지역·세대·형편에 따라 달라질 수 있습니다.</p>', src_html()]
    write("/about/", layout("/about/", "데이터 설명", "우아경조사가 사용하는 설문·법령 자료와 금액 기준 산정 방식을 설명합니다.", "\n".join(body), None, [("홈", "/"), ("데이터 설명", "/about/")]), "0.3")
    body = ['<div class="page-head"><h1>개인정보처리방침</h1></div>', '<p class="lead">우아경조사는 회원가입·로그인 없이 이용하며 개인정보를 수집하지 않습니다. 금액 계산기는 브라우저 안에서만 동작하고 입력값을 서버로 보내지 않습니다. 사이트 개선을 위해 Google Analytics를 사용하고, 광고 게재를 위해 Google AdSense와 쿠팡 파트너스를 사용하며 이 과정에서 쿠키가 사용될 수 있습니다.</p>']
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아경조사 개인정보처리방침", "\n".join(body), None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)


def finish():
    shutil.copytree(ROOT / "assets", OUT / "assets")
    for nf in ROOT.glob("naver*.html"):
        shutil.copy(nf, OUT / nf.name)
    today = TODAY.isoformat()
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), today, pr) for p, pr in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooagyeongjo.wooahouse.com\n", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈으로</a><a class="chip" href="/축의금/">축의금</a><a class="chip" href="/조의금/">조의금</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("페이지", len(WRITTEN), "(sitemap)")


if __name__ == "__main__":
    build()
