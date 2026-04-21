import streamlit as st
from supabase import create_client
import pandas as pd
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import random
from scipy import stats

# 1. 초기 설정
st.set_page_config(page_title="의사결정 스타일 연구", layout="wide")

# Supabase 연결
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("데이터베이스 연결 설정이 필요합니다.")

# 2. 유니버설 키워드 사전 (동일 차원 내 공용)
KEYWORDS = {
    "T": { 
        "C_scenario": "오늘 당장 사고 싶은 물건(아이패드, 운동화 등)을 위해 주식 매매를 결정하는 상황입니다.",
        "D_scenario": "대학 졸업 후 10년 뒤, 내 집 마련이나 창업을 위한 종잣돈(Seed Money)을 굴리는 상황입니다.",
        "abs": ["경제적독립", "미래설계", "자산형성", "꿈의실현", "가치투자", "안정감", "성공", "자기만족"],
        "con": ["매수클릭", "단타매매", "수수료", "차트분석", "급등주", "계좌입금", "매도타이밍", "수익률확인"]
    },
    "S": { 
        "C_scenario": "알바로 힘들게 번 200만 원을 어디에 투자할지 직접 결정하는 상황입니다.",
        "D_scenario": "온라인 게시판에 고민 글을 올린 이름 모를 학우에게 투자 포트폴리오를 조언해 주는 상황입니다.",
        "abs": ["투자원칙", "포트폴리오", "합리적선택", "리스크분산", "시장흐름", "재무계획", "통찰력", "전문성"],
        "con": ["원금손실", "불안함", "송금기록", "계좌잔고", "매수버튼", "공동인증서", "이체한도", "실시간알림"]
    },
    "L": { 
        "C_scenario": "내가 매일 사용하는 서비스인 카카오, 네이버 등 익숙한 국내 기업에 투자하는 상황입니다.",
        "D_scenario": "한 번도 가본 적 없는 실리콘밸리의 AI 스타트업이나 북유럽의 친환경 에너지 기업에 투자하는 상황입니다.",
        "abs": ["기술혁신", "인류의미래", "패러다임", "유망산업", "글로벌트렌드", "비전", "성장동력", "잠재력"],
        "con": ["뉴스검색", "재무제표", "거래비용", "실시간시세", "주가흐름", "투자정보", "수익률추이", "모바일앱"]
    },
    "H": { 
        "C_scenario": "토스나 카카오뱅크 파킹통장에 넣어두고 매일 확실한 이자를 받는 상황입니다.",
        "D_scenario": "성공하면 대박이지만 휴지조각이 될 확률이 99%인 유행하는 밈코인에 투자하는 상황입니다.",
        "abs": ["일확천금", "인생역전", "기회", "희망", "짜릿함", "승부수", "가능성", "자유"],
        "con": ["예금금리", "비상금", "자동이체", "이자문자", "가입금액", "해지버튼", "보안카드", "입출금내역"]
    }
}

# 3. 세션 초기화
if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "user_type": None, "class_name": None, "step": 0, "results": []})

# 4. 로그인 및 수업 선택
if not st.session_state.logged_in:
    st.title("의사결정 스타일 및 심리 선호도 조사")
    user_type = st.radio("로그인 유형", ["학생", "교수"])
    if user_type == "교수":
        pw = st.text_input("비밀번호", type="password")
        if pw == "3383" and st.button("교수 로그인"):
            st.session_state.update({"logged_in": True, "user_type": "prof"})
            st.rerun()
    else:
        name = st.text_input("성함")
        cls = st.selectbox("참여 중인 수업", ["인하대 행동재무학", "숙대 1", "숙대 2"])
        if name and st.button("실험 참여"):
            st.session_state.update({
                "logged_in": True, "user_type": "student", "student_name": name, 
                "class_name": cls, "order": random.choice(['A', 'B']) # 순서 효과 방지
            })
            st.rerun()

# 5. 교수 화면 (Admin)
elif st.session_state.user_type == "prof":
    st.sidebar.title("👨‍🏫 관리자 패널")
    target_cls = st.sidebar.selectbox("수업 선택", ["인하대 행동재무학", "숙대 1", "숙대 2"])
    
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("1. 대기 모드"): supabase.table("construal_state").update({"current_state": "standby"}).eq("class_name", target_cls).execute()
    if c2.button("2. 실험 시작"): supabase.table("construal_state").update({"current_state": "active"}).eq("class_name", target_cls).execute()
    if c3.button("3. 결과 확인"): supabase.table("construal_state").update({"current_state": "result"}).eq("class_name", target_cls).execute()
    if c4.button("데이터 새로고침"): st.rerun()

    data = supabase.table("construal_result").select("*").eq("class_name", target_cls).execute()
    df = pd.DataFrame(data.data)

    if not df.empty and len(df) > 0:
        st.divider()
        st.header(f"📊 {target_cls} 실험 결과 분석 리포트")
        st.write(f"현재 제출된 총 응답 수: {len(df)}건")
        
        # 1) 워드클라우드 (근거리 vs 원거리 비교)
        st.subheader("심리적 거리별 키워드 비교 (Word Cloud)")
        wc_col1, wc_col2 = st.columns(2)
        
        words_c = [w for l in df[df['module_type'].str.contains('_C')]['selected_keywords'] for w in l]
        words_d = [w for l in df[df['module_type'].str.contains('_D')]['selected_keywords'] for w in l]
        
        font_path = 'NanumGothic.ttf'
        
        with wc_col1:
            st.write("📍 **근거리 상황 (Close)**")
            if words_c:
                try:
                    wc_c = WordCloud(font_path=font_path, background_color="white", width=400, height=300).generate(" ".join(words_c))
                    st.image(wc_c.to_array())
                except:
                    st.write("(폰트 파일을 찾을 수 없습니다.)")
        with wc_col2:
            st.write("🌐 **원거리 상황 (Distant)**")
            if words_d:
                try:
                    wc_d = WordCloud(font_path=font_path, background_color="white", width=400, height=300).generate(" ".join(words_d))
                    st.image(wc_d.to_array())
                except:
                    st.write("(폰트 파일을 찾을 수 없습니다.)")

        # 2) 마인드 맵 좌표
        st.subheader("해석 수준 마인드 맵 (Construal Level Map)")
        st.write("각 점은 특정 상황에서 선택한 3개 단어의 조합입니다. Y축은 상위 수준 단어의 개수입니다.")
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(df['score_concrete'], df['score_abstract'], alpha=0.3, color='blue')
        ax.set_xlabel("Concrete Score (하위 수준)"); ax.set_ylabel("Abstract Score (상위 수준)")
        ax.set_xticks([0, 1, 2, 3]); ax.set_yticks([0, 1, 2, 3])
        st.pyplot(fig)

        # 3) 자기 우월평가
        st.subheader("자기 우월평가(Overplacement) 분석")
        avg_op = df[['overplacement_1', 'overplacement_2', 'overplacement_3']].mean().mean()
        st.metric("집단 평균 자기 능력 백분위", f"{avg_op:.1f}%", delta=f"{avg_op-50:.1f}% (50% 기준)")
        st.info(f"**분석:** 응답 평균이 {avg_op:.1f}%로 나타난 것은 대다수 학생이 자신을 '평균 이상'으로 믿는 편향을 보여줍니다. 이는 **사회적 거리**가 먼 '일반인'을 비교 대상으로 두었을 때, 타인을 추상적이고 평범하게 인식하여 상대적으로 자신을 우월하게 평가하는 현상입니다.")

        # 4) 순서 효과 검증
        st.subheader("순서 효과(Order Effect) 통계 검증")
        group_a = df[df['order_type'] == 'A']['score_abstract']
        group_b = df[df['order_type'] == 'B']['score_abstract']
        
        if len(group_a) > 0 and len(group_b) > 0:
            t_stat, p_val = stats.ttest_ind(group_a, group_b, equal_var=False)
            st.write(f"- 그룹 A(근거리 우선) 추상성 평균: {group_a.mean():.2f}")
            st.write(f"- 그룹 B(원거리 우선) 추상성 평균: {group_b.mean():.2f}")
            st.write(f"- **t-통계량:** {t_stat:.4f}, **p-value:** {p_val:.4f}")
            
            if p_val > 0.05:
                st.success("검증 결과: p-value가 0.05보다 크므로 순서에 따른 유의미한 차이가 없습니다. 실험 설계가 안정적입니다.")
            else:
                st.warning("검증 결과: p-value가 0.05 이하이므로 순서 효과가 존재할 가능성이 있습니다.")

# 6. 학생 화면 (Student)
else:
    state = supabase.table("construal_state").select("*").eq("class_name", st.session_state.class_name).execute().data[0]
    
    if state['current_state'] == "standby":
        st.info("실험 준비 중입니다. 교수님의 안내를 기다려 주세요.")
        if st.button("화면 새로고침"): st.rerun()
    
    elif state['current_state'] == "active":
        # 상단 진행 바
        st.progress(st.session_state.step / 8)
        st.write(f"**진행 단계: {st.session_state.step}/8**")

        dims = ["T", "S", "L", "H"]
        flat_steps = []
        for d in dims:
            p = [f"{d}_C", f"{d}_D"]
            if st.session_state.order == 'B': p = p[::-1]
            flat_steps.extend(p)

        if st.session_state.step < 8:
            curr = flat_steps[st.session_state.step]
            dim_key, type_key = curr.split('_')
            st.subheader(f"상황 {st.session_state.step + 1}")
            st.info(KEYWORDS[dim_key][f"{type_key}_scenario"])
            
            words = KEYWORDS[dim_key]["abs"] + KEYWORDS[dim_key]["con"]
            random.seed(st.session_state.step); random.shuffle(words)

            if f"sel_{curr}" not in st.session_state: st.session_state[f"sel_{curr}"] = []
            
            cols = st.columns(4)
            for i, w in enumerate(words):
                if cols[i%4].checkbox(w, key=f"chk_{curr}_{w}"):
                    if w not in st.session_state[f"sel_{curr}"]: st.session_state[f"sel_{curr}"].append(w)
                else:
                    if w in st.session_state[f"sel_{curr}"]: st.session_state[f"sel_{curr}"].remove(w)
            
            if len(st.session_state[f"sel_{curr}"]) == 3:
                if st.button("다음으로"):
                    sel = st.session_state[f"sel_{curr}"]
                    s_abs = len([x for x in sel if x in KEYWORDS[dim_key]["abs"]])
                    s_con = len([x for x in sel if x in KEYWORDS[dim_key]["con"]])
                    st.session_state.results.append({
                        "type": curr, "words": sel, "abs": s_abs, "con": s_con, "order": st.session_state.order
                    })
                    st.session_state.step += 1
                    st.rerun()
            elif len(st.session_state[f"sel_{curr}"]) > 3:
                st.warning("단어는 3개까지만 선택할 수 있습니다.")

        elif st.session_state.step == 8:
            st.subheader("마지막 설문")
            st.write("다른 사람들과 비교했을 때 나의 능력은 상위 몇 %입니까? (0: 최하위, 100: 최상위)")
            op1 = st.slider("1. 투자자로서의 나의 능력", 0, 100, 50)
            op2 = st.slider("2. 투자 시장의 흐름을 판단하는 능력", 0, 100, 50)
            op3 = st.slider("3. 투자 정보 중 가치 있는 정보를 골라내는 능력", 0, 100, 50)
            
            if st.button("최종 제출"):
                for r in st.session_state.results:
                    supabase.table("construal_result").insert({
                        "class_name": st.session_state.class_name, "student_name": st.session_state.student_name,
                        "order_type": r["order"], "module_type": r["type"], "selected_keywords": r["words"],
                        "score_abstract": r["abs"], "score_concrete": r["con"],
                        "overplacement_1": op1, "overplacement_2": op2, "overplacement_3": op3
                    }).execute()
                st.success("응답이 성공적으로 제출되었습니다. 감사합니다.")
                st.session_state.step += 1
    
    else:
        st.success("모든 실험 과정이 끝났습니다. 교수님의 화면을 주목해주세요.")