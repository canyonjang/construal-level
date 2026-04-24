import streamlit as st
from supabase import create_client
import pandas as pd
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import random
from scipy import stats

# 1. 초기 설정 및 DB 연결
st.set_page_config(page_title="해석수준이론과 자기과신", layout="wide")

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("데이터베이스 연결 설정(secrets.toml)을 확인해주세요.")

# 2. 키워드 사전 (동일 차원 내 공용)
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
    st.title("해석수준이론과 자기과신")
    user_type = st.radio("로그인", ["학생", "교수"])
    if user_type == "교수":
        pw = st.text_input("비밀번호", type="password")
        if pw == "3383" and st.button("로그인"):
            st.session_state.update({"logged_in": True, "user_type": "prof"})
            st.rerun()
    else:
        name = st.text_input("별명")
        if name and st.button("참여하기"):
            active_class_res = supabase.table("construal_state").select("class_name").eq("current_state", "active").execute()
            if active_class_res.data:
                active_class = active_class_res.data[0]['class_name']
                
                # 50:50 균등 배정 로직
                current_logs = supabase.table("student_logs").select("id").eq("class_name", active_class).execute().data
                current_count = len(current_logs)
                assigned_order = 'A' if current_count % 2 == 0 else 'B'
                
                st.session_state.update({
                    "logged_in": True, 
                    "user_type": "student", 
                    "student_name": name, 
                    "class_name": active_class, 
                    "order": assigned_order
                })
                supabase.table("student_logs").insert({"class_name": active_class, "student_name": name}).execute()
                st.rerun()
            else:
                st.warning("현재 진행 중인 수업이 없습니다. 교수님의 시작 신호를 기다려 주세요.")

# 5. 교수 화면 (Admin Panel)
elif st.session_state.user_type == "prof":
    st.sidebar.title("관리자 패널")
    target_cls = st.sidebar.selectbox("수업 선택", ["인하대 행동재무학", "숙대 1", "숙대 2"])
    
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("실험 시작"): 
        supabase.table("construal_state").update({"current_state": "active"}).eq("class_name", target_cls).execute()
    if c2.button("결과 확인"): 
        supabase.table("construal_state").update({"current_state": "result"}).eq("class_name", target_cls).execute()
    if c3.button("데이터 새로고침"): 
        st.rerun()
    if c4.button("데이터 초기화"):
        supabase.table("construal_result").delete().eq("class_name", target_cls).execute()
        supabase.table("student_logs").delete().eq("class_name", target_cls).execute()
        supabase.table("construal_state").update({"current_state": "standby"}).eq("class_name", target_cls).execute()
        st.success(f"'{target_cls}'의 모든 데이터가 초기화되었습니다.")
        st.rerun()

    login_count = len(supabase.table("student_logs").select("student_name", count="exact").eq("class_name", target_cls).execute().data)
    res_data_count = supabase.table("construal_result").select("student_name").eq("class_name", target_cls).execute().data
    df_count = pd.DataFrame(res_data_count)
    complete_count = len(df_count['student_name'].unique()) if not df_count.empty else 0
    
    st.sidebar.metric("로그인한 학생 수", f"{login_count}명")
    st.sidebar.metric("응답 완료 학생 수", f"{complete_count}명")
    st.sidebar.write(f"현재 제출된 총 응답 건수: {len(df_count)}건")

    data = supabase.table("construal_result").select("*").eq("class_name", target_cls).execute()
    df = pd.DataFrame(data.data)

    if not df.empty:
        st.divider()
        st.header(f"실험 결과 분석 리포트")
        
        # 1) 워드클라우드
        st.subheader("심리적 거리별 키워드 비교 (Word Cloud)")
        wc_col1, wc_col2 = st.columns(2)
        font_path = 'NanumGothic.ttf'
        
        with wc_col1:
            st.write("📍 **근거리 상황 (Close)**")
            words_c = [w for l in df[df['module_type'].str.contains('_C')]['selected_keywords'] for w in l]
            if words_c: st.image(WordCloud(font_path=font_path, background_color="white", width=400).generate(" ".join(words_c)).to_array())
        
        with wc_col2:
            st.write("🌐 **원거리 상황 (Distant)**")
            words_d = [w for l in df[df['module_type'].str.contains('_D')]['selected_keywords'] for w in l]
            if words_d: st.image(WordCloud(font_path=font_path, background_color="white", width=400).generate(" ".join(words_d)).to_array())

        # 2) 차원별 비교 막대그래프
        st.subheader("4대 심리적 차원별 해석 수준(추상성) 비교")
        
        dim_map = {'T': 'Temporal', 'S': 'Social', 'L': 'Spatial', 'H': 'Hypothetical'}
        df_chart = df.copy()
        df_chart['Dimension'] = df_chart['module_type'].apply(lambda x: dim_map.get(x.split('_')[0], x))
        df_chart['Distance'] = df_chart['module_type'].apply(lambda x: 'Close' if '_C' in x else 'Distant')
        avg_scores = df_chart.groupby(['Dimension', 'Distance'])['score_abstract'].mean().unstack()
        
        ordered_dims = ['Temporal', 'Social', 'Spatial', 'Hypothetical']
        existing_dims = [d for d in ordered_dims if d in avg_scores.index]
        avg_scores = avg_scores.reindex(existing_dims)
        
        fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
        x = np.arange(len(avg_scores.index))
        width = 0.35
        
        if 'Close' in avg_scores.columns:
            ax_bar.bar(x - width/2, avg_scores['Close'], width, label='Close (Concrete)', color='royalblue', alpha=0.8)
        if 'Distant' in avg_scores.columns:
            ax_bar.bar(x + width/2, avg_scores['Distant'], width, label='Distant (Abstract)', color='crimson', alpha=0.8)
        
        ax_bar.set_ylabel('Avg Abstractness Score')
        ax_bar.set_title('Changes in Construal Level by Distance')
        ax_bar.set_xticks(x)
        ax_bar.set_xticklabels(avg_scores.index)
        ax_bar.set_ylim(0, 3.5)
        ax_bar.legend(loc='upper left')
        
        for i in x:
            if 'Close' in avg_scores.columns:
                val = avg_scores['Close'].iloc[i] if not np.isnan(avg_scores['Close'].iloc[i]) else 0
                ax_bar.text(i - width/2, val + 0.05, f"{val:.2f}", ha='center', fontweight='bold', color='royalblue')
            if 'Distant' in avg_scores.columns:
                val = avg_scores['Distant'].iloc[i] if not np.isnan(avg_scores['Distant'].iloc[i]) else 0
                ax_bar.text(i + width/2, val + 0.05, f"{val:.2f}", ha='center', fontweight='bold', color='crimson')
        
        ax_bar.spines['top'].set_visible(False)
        ax_bar.spines['right'].set_visible(False)
        st.pyplot(fig_bar)

        # 3) 순서 효과(Order Effect) 분석
        st.divider()
        st.subheader("순서 효과(Order Effect) 통계 검증")
        group_a = df[df['order_type'] == 'A']['score_abstract']
        group_b = df[df['order_type'] == 'B']['score_abstract']
        
        if len(group_a) > 2 and len(group_b) > 2:
            t_stat, p_val_order = stats.ttest_ind(group_a, group_b, equal_var=False)
            st.write(f"- 그룹 A(근거리 우선) 전체 추상성 평균: **{group_a.mean():.2f}**")
            st.write(f"- 그룹 B(원거리 우선) 전체 추상성 평균: **{group_b.mean():.2f}**")
            st.write(f"- **t-통계량:** {t_stat:.4f}, **유의확률 (p-value):** {p_val_order:.4f}")
            
            if p_val_order > 0.05:
                st.success("검증 결과: p-value가 0.05보다 크므로 제시 순서에 따른 유의미한 차이가 없습니다. (문항 순서 효과 통제 성공)")
            else:
                st.warning("검증 결과: p-value가 0.05 이하이므로 제시 순서에 따른 차이(순서 효과)가 존재할 가능성이 있습니다.")
        else:
            st.write("각 그룹(A, B)의 데이터가 충분히 수집되면 순서 효과 검증 결과가 표시됩니다.")

        # 4) 자기 우월평가 분석 및 상관관계
        st.divider()
        st.subheader("자기 우월평가(Overplacement) 분석")
        avg_op = df[['overplacement_1', 'overplacement_2', 'overplacement_3']].mean().mean()
        st.metric("집단 평균 자기 능력 백분위", f"{avg_op:.1f}%", delta=f"{avg_op-50:.1f}% (50% 기준)")
        
        # 개인별 자기 우월평가 결과 (별명, 상위 %)
        st.subheader("개인별 자기 우월평가 결과")
        df_op = df[['student_name', 'overplacement_1', 'overplacement_2', 'overplacement_3']].drop_duplicates()
        df_op['op_avg'] = df_op[['overplacement_1', 'overplacement_2', 'overplacement_3']].mean(axis=1)
        df_op['top_pct'] = df_op['op_avg'].rank(pct=True, ascending=False) * 100
        
        df_display = df_op[['student_name', 'op_avg', 'top_pct']].copy()
        df_display.columns = ['별명', '평균 점수', '상위 %']
        df_display = df_display.sort_values(by='상위 %', ascending=True).reset_index(drop=True)
        st.dataframe(df_display.style.format({'평균 점수': '{:.1f}', '상위 %': '상위 {:.1f}%'}))
        
        st.write("---")
        st.subheader("사회적 거리와 자기 우월평가의 상관관계")
        social_df = df[df['module_type'] == 'S_D'].copy()
        social_df['op_avg'] = social_df[['overplacement_1', 'overplacement_2', 'overplacement_3']].mean(axis=1)
        
        if len(social_df) > 2:
            corr, p_val = stats.pearsonr(social_df['score_abstract'], social_df['op_avg'])
            st.write(f"**통계 분석 결과:**")
            st.write(f"- 상관계수 (Pearson r): **{corr:.4f}**")
            st.write(f"- 유의확률 (p-value): **{p_val:.4f}**")
            
            if p_val < 0.05:
                st.success("분석 결과: 사회적 거리의 추상성 점수가 높을수록 자기 우월평가 점수도 높다는 가설이 통계적으로 유의미하게 나타났습니다.")
            else:
                st.info("분석 결과: 사회적 거리의 추상성 점수가 높을수록 자기 우월평가 점수가 높게 나타나는 경향성이 있으나, 아직 통계적 유의성(p < 0.05)이 확보되지 않았습니다.")
            
            st.caption("※ 해설: 타인을 구체적인 개인이 아닌 '추상적인 평균'으로 인식(추상성 점수 증가)할수록, 자신을 타인보다 더 특별하고 우월하게 평가하는 편향(Overplacement)이 짙어짐을 의미합니다.")
        
        # 개인별 상관관계 산점도
        st.subheader("개인별 상관관계 산점도")
        if not social_df.empty:
            fig_scatter, ax_scatter = plt.subplots(figsize=(8, 5))
            ax_scatter.scatter(social_df['score_abstract'], social_df['op_avg'], color='purple', alpha=0.6)
            
            for i, row in social_df.iterrows():
                ax_scatter.text(row['score_abstract'], row['op_avg'] + 1.5, row['student_name'], fontsize=9, ha='center', va='bottom')
                
            ax_scatter.set_xlabel("Abstractness Score (S_D)")
            ax_scatter.set_ylabel("Overplacement Average Score")
            ax_scatter.set_xticks([0, 1, 2, 3])
            
            ax_scatter.spines['top'].set_visible(False)
            ax_scatter.spines['right'].set_visible(False)
            
            st.pyplot(fig_scatter)
        else:
            st.write("데이터가 충분히 수집되면 산점도가 표시됩니다.")

# 6. 학생 화면
else:
    state = supabase.table("construal_state").select("*").eq("class_name", st.session_state.class_name).execute().data[0]
    st.title(st.session_state.class_name)
    
    if state['current_state'] == "standby":
        st.info("교수님의 시작 신호를 기다리고 있습니다...")
        if st.button("화면 새로고침"): st.rerun()
        
    elif state['current_state'] == "active":
        if st.session_state.step < 9:
            st.write(f"**현재 진행 단계: {st.session_state.step + 1}/9**")
            st.progress((st.session_state.step + 1) / 9)
            
            # 8단계(마지막 설문) 이전까지만 안내 문구 노출
            if st.session_state.step < 8:
                st.info("💡 **각 상황을 충분히 몰입해서 읽고, 당신의 머릿속에 가장 비중 있게 떠오르는 단어 3개를 선택하세요.**")
        
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
            
            st.markdown(f"**{KEYWORDS[dim_key][f'{type_key}_scenario']}**")
            
            if f"word_list_{st.session_state.step}" not in st.session_state:
                all_list = KEYWORDS[dim_key]["abs"] + KEYWORDS[dim_key]["con"]
                random.shuffle(all_list)
                st.session_state[f"word_list_{st.session_state.step}"] = all_list
            
            current_words = st.session_state[f"word_list_{st.session_state.step}"]
            
            selected = []
            cols = st.columns(4)
            for i, w in enumerate(current_words):
                if cols[i%4].checkbox(w, key=f"{curr}_{w}"): selected.append(w)
                
            if len(selected) == 3 and st.button("다음"):
                s_abs = len([x for x in selected if x in KEYWORDS[dim_key]["abs"]])
                s_con = len([x for x in selected if x in KEYWORDS[dim_key]["con"]])
                st.session_state.results.append({
                    "type": curr, "abs": s_abs, "con": s_con, "words": selected
                })
                st.session_state.step += 1
                st.rerun()
            elif len(selected) > 3:
                st.warning("단어는 3개까지만 선택 가능합니다.")

        elif st.session_state.step == 8:
            st.write("다른 사람들과 비교했을 때 나의 투자 능력은 상위 몇 %입니까? (0: 최하위, 100: 최상위)")
            op1 = st.slider("1. 투자자로서의 나의 능력", 0, 100, 50)
            op2 = st.slider("2. 투자 시장 흐름 판단 능력", 0, 100, 50)
            op3 = st.slider("3. 가치 있는 정보 선별 능력", 0, 100, 50)
            
            if st.button("제출하기"):
                for r in st.session_state.results:
                    supabase.table("construal_result").insert({
                        "class_name": st.session_state.class_name, 
                        "student_name": st.session_state.student_name, 
                        "order_type": st.session_state.order, 
                        "module_type": r["type"], 
                        "selected_keywords": r["words"], 
                        "score_abstract": r["abs"], 
                        "score_concrete": r["con"], 
                        "overplacement_1": op1, 
                        "overplacement_2": op2, 
                        "overplacement_3": op3
                    }).execute()
                st.session_state.step += 1 
                st.rerun()
                
        elif st.session_state.step == 9:
            st.success("🎉 성공적으로 제출되었습니다! 강의실 화면에서 결과를 확인하세요.")
    
    else:
        st.success("모든 실험이 완료되었습니다. 교수님의 화면을 확인해주세요.")
