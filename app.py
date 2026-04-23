import streamlit as st
from supabase import create_client
import pandas as pd
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import random
from scipy import stats

# 1. 초기 설정 및 DB 연결
st.set_page_config(page_title="Construal Level & Overconfidence", layout="wide")

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Please check your database connection settings.")

# 2. 키워드 사전 (방법 A: 동일 차원 내 공용)
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
        "C_scenario": "토스나 카카오뱅크 파킹통장에 넣어두고 매일 확실한 이자가 받는 상황입니다.",
        "D_scenario": "성공하면 대박이지만 휴지조각이 될 확률이 99%인 유행하는 밈코인에 투자하는 상황입니다.",
        "abs": ["일확천금", "인생역전", "기회", "희망", "짜릿함", "승부수", "가능성", "자유"],
        "con": ["예금금리", "비상금", "자동이체", "이자문자", "가입금액", "해지버튼", "보안카드", "입출금내역"]
    }
}

# 3. 세션 초기화
if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "user_type": None, "class_name": None, "step": 0, "results": []})

# 4. 로그인 화면
if not st.session_state.logged_in:
    st.title("Construal Level Theory & Overconfidence")
    user_type = st.radio("Login", ["Student", "Professor"])
    if user_type == "Professor":
        pw = st.text_input("Password", type="password")
        if pw == "3383" and st.button("Login"):
            st.session_state.update({"logged_in": True, "user_type": "prof"})
            st.rerun()
    else:
        name = st.text_input("Name")
        if name and st.button("Join"):
            active_class_res = supabase.table("construal_state").select("class_name").eq("current_state", "active").execute()
            if active_class_res.data:
                active_class = active_class_res.data[0]['class_name']
                st.session_state.update({"logged_in": True, "user_type": "student", "student_name": name, "class_name": active_class, "order": random.choice(['A', 'B'])})
                supabase.table("student_logs").insert({"class_name": active_class, "student_name": name}).execute()
                st.rerun()
            else:
                st.warning("No active session. Please wait for the professor.")

# 5. 교수 화면 (시각화 영문화 반영)
elif st.session_state.user_type == "prof":
    st.sidebar.title("Admin Panel")
    target_cls = st.sidebar.selectbox("Select Class", ["인하대 행동재무학", "숙대 1", "숙대 2"])
    
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Standby Mode"): supabase.table("construal_state").update({"current_state": "standby"}).eq("class_name", target_cls).execute()
    if c2.button("Start Experiment"): supabase.table("construal_state").update({"current_state": "active"}).eq("class_name", target_cls).execute()
    if c3.button("Show Results"): supabase.table("construal_state").update({"current_state": "result"}).eq("class_name", target_cls).execute()
    
    if c4.button("Refresh Data"):
        login_count = len(supabase.table("student_logs").select("student_name", count="exact").eq("class_name", target_cls).execute().data)
        res_data = supabase.table("construal_result").select("student_name").eq("class_name", target_cls).execute().data
        df_res = pd.DataFrame(res_data)
        complete_count = len(df_res['student_name'].unique()) if not df_res.empty else 0
        st.sidebar.metric("Logged-in Students", f"{login_count}")
        st.sidebar.metric("Completed Students", f"{complete_count}")
        st.sidebar.write(f"Total Responses: {len(df_res)}")

    data = supabase.table("construal_result").select("*").eq("class_name", target_cls).execute()
    df = pd.DataFrame(data.data)

    if not df.empty:
        st.divider()
        st.header(f"Analysis Report: {target_cls}")
        
        # 1) 워드클라우드 (영문 타이틀)
        st.subheader("Comparison of Keywords by Psychological Distance")
        wc_col1, wc_col2 = st.columns(2)
        font_path = 'NanumGothic.ttf' # 키워드 데이터가 한글일 경우 필요
        
        with wc_col1:
            st.write("📍 **Close Distance Situation**")
            words_c = [w for l in df[df['module_type'].str.contains('_C')]['selected_keywords'] for w in l]
            if words_c: st.image(WordCloud(font_path=font_path, background_color="white", width=400).generate(" ".join(words_c)).to_array())
        
        with wc_col2:
            st.write("🌐 **Distant Distance Situation**")
            words_d = [w for l in df[df['module_type'].str.contains('_D')]['selected_keywords'] for w in l]
            if words_d: st.image(WordCloud(font_path=font_path, background_color="white", width=400).generate(" ".join(words_d)).to_array())

        # 2) 차원별 비교 막대그래프 (영문화)
        st.subheader("Abstractness Score by 4 Psychological Dimensions")
        dim_map = {'T': 'Temporal', 'S': 'Social', 'L': 'Spatial', 'H': 'Hypothetical'}
        df_chart = df.copy()
        df_chart['Dimension'] = df_chart['module_type'].apply(lambda x: dim_map.get(x.split('_')[0], x))
        df_chart['Distance'] = df_chart['module_type'].apply(lambda x: 'Close' if '_C' in x else 'Distant')
        avg_scores = df_chart.groupby(['Dimension', 'Distance'])['score_abstract'].mean().unstack()
        
        fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
        x = np.arange(len(avg_scores.index))
        width = 0.35
        if 'Close' in avg_scores.columns:
            ax_bar.bar(x - width/2, avg_scores['Close'], width, label='Close (Concrete)', color='royalblue', alpha=0.8)
        if 'Distant' in avg_scores.columns:
            ax_bar.bar(x + width/2, avg_scores['Distant'], width, label='Distant (Abstract)', color='crimson', alpha=0.8)
        
        ax_bar.set_ylabel('Avg Abstractness Score')
        ax_bar.set_xticks(x)
        ax_bar.set_xticklabels(avg_scores.index)
        ax_bar.set_ylim(0, 3.5)
        ax_bar.legend()
        st.pyplot(fig_bar)

        # 3) 마인드 맵 좌표 (영문화)
        st.subheader("Construal Level Map (Concreteness vs Abstractness)")
        fig, ax = plt.subplots(figsize=(8, 5))
        colors = np.where(df['module_type'].str.contains('_C'), 'blue', 'red')
        ax.scatter(df['score_concrete'], df['score_abstract'], c=colors, alpha=0.4)
        ax.set_xlabel("Concreteness Score")
        ax.set_ylabel("Abstractness Score")
        ax.set_xticks([0,1,2,3]); ax.set_yticks([0,1,2,3])
        st.pyplot(fig)
        st.write("**Note:** Blue dots (Close) tend toward the bottom-right, while Red dots (Distant) move toward the top-left.")

        # 4) 자기 우월평가 분석
        st.subheader("Overplacement Analysis")
        avg_op = df[['overplacement_1', 'overplacement_2', 'overplacement_3']].mean().mean()
        st.metric("Group Avg Percentile", f"{avg_op:.1f}%", delta=f"{avg_op-50:.1f}%")
        
        social_df = df[df['module_type'] == 'S_D'].copy()
        social_df['op_avg'] = social_df[['overplacement_1', 'overplacement_2', 'overplacement_3']].mean(axis=1)
        if len(social_df) > 2:
            corr, p_val = stats.pearsonr(social_df['score_abstract'], social_df['op_avg'])
            st.write(f"- Correlation (Abstractness vs Overplacement): **{corr:.4f}** (p={p_val:.4f})")
            st.info("Abstract perception of others often correlates with higher self-overplacement.")

# 6. 학생 화면
else:
    state = supabase.table("construal_state").select("*").eq("class_name", st.session_state.class_name).execute().data[0]
    st.title(st.session_state.class_name)
    if state['current_state'] == "standby":
        st.info("Waiting for the professor to start the session...")
        if st.button("Refresh"): st.rerun()
    elif state['current_state'] == "active":
        st.progress(st.session_state.step / 9)
        st.write(f"**Step: {st.session_state.step}/9**")
        dims = ["T", "S", "L", "H"]
        flat_steps = []
        for d in dims:
            p = [f"{d}_C", f"{d}_D"]
            if st.session_state.order == 'B': p = p[::-1]
            flat_steps.extend(p)

        if st.session_state.step < 8:
            curr = flat_steps[st.session_state.step]
            dim_key, type_key = curr.split('_')
            st.subheader(f"Situation {st.session_state.step + 1}")
            st.markdown(f"**{KEYWORDS[dim_key][f'{type_key}_scenario']}**\n\n👉 *Select 3 words appropriate for this situation.*")
            all_list = KEYWORDS[dim_key]["abs"] + KEYWORDS[dim_key]["con"]
            random.seed(st.session_state.step); random.shuffle(all_list)
            selected = []
            cols = st.columns(4)
            for i, w in enumerate(all_list):
                if cols[i%4].checkbox(w, key=f"{curr}_{w}"): selected.append(w)
            if len(selected) == 3 and st.button("Next"):
                st.session_state.results.append({"type": curr, "abs": len([x for x in selected if x in KEYWORDS[dim_key]["abs"]]), "con": len([x for x in selected if x in KEYWORDS[dim_key]["con"]]), "words": selected})
                st.session_state.step += 1
                st.rerun()
        elif st.session_state.step == 8:
            st.write("Compared to others, what percentile is your investment ability? (0: Lowest, 100: Highest)")
            op1 = st.slider("1. My ability as an investor", 0, 100, 50)
            op2 = st.slider("2. Market trend judgment ability", 0, 100, 50)
            op3 = st.slider("3. Valuable information screening ability", 0, 100, 50)
            if st.button("Submit"):
                for r in st.session_state.results:
                    supabase.table("construal_result").insert({"class_name": st.session_state.class_name, "student_name": st.session_state.student_name, "order_type": st.session_state.order, "module_type": r["type"], "selected_keywords": r["words"], "score_abstract": r["abs"], "score_concrete": r["con"], "overplacement_1": op1, "overplacement_2": op2, "overplacement_3": op3}).execute()
                st.success("Thank you for participating!"); st.session_state.step += 1
    else: st.success("Experiment finished.")
