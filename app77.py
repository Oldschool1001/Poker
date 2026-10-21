import streamlit as st
import random
import pandas as pd
import re
from treys import Card, Evaluator

st.set_page_config(page_title="Poker RWA Tool", layout="wide")
st.title("🃏 Advanced Poker Flexible Analyser (Hand & Range Mode)")

ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
PRESETS = {
    "Manuelle Auswahl (Leer)": {},
    "UTG Range (~15%)": {h: 1.0 for h in ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "AKs", "AQs", "AJs", "ATs", "A9s", "KQs", "KJs", "KTs", "QJs", "QTs", "JTs", "T9s", "AKo", "AQo", "AJo"]},
    "MP Range (~20%)": {h: 1.0 for h in ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "KQs", "KJs", "KTs", "QJs", "QTs", "JTs", "T9s", "98s", "87s", "AKo", "AQo", "AJo", "ATo", "KQo"]},
    "CO Range (~28%)": {h: 1.0 for h in ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s", "KQs", "KJs", "KTs", "K9s", "K8s", "QJs", "QTs", "Q9s", "JTs", "J9s", "T9s", "T8s", "98s", "97s", "87s", "76s", "65s", "54s", "AKo", "AQo", "AJo", "ATo", "A9o", "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"]},
    "BTN Range (~40%)": {h: 1.0 for h in ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22", "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s", "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "QJs", "QTs", "Q9s", "JTs", "J9s", "T9s", "T8s", "98s", "97s", "87s", "76s", "65s", "54s", "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"]},
    "SB Range (~45%)": {h: 1.0 for h in ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22", "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s", "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s", "K5s", "QJs", "QTs", "Q9s", "Q8s", "JTs", "J9s", "T9s", "T8s", "98s", "97s", "87s", "76s", "65s", "54s", "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"]},
    "3-Bet Range (~10%)": {h: 1.0 for h in ["AA", "KK", "QQ", "JJ", "TT", "AKs", "AQs", "AJs", "A5s", "A4s", "KQs", "KJs", "QJs", "JTs", "AKo", "AQo"]}
}

if 'selected_range_hero' not in st.session_state: st.session_state.selected_range_hero = {}
if 'selected_range_villain' not in st.session_state: st.session_state.selected_range_villain = {}
if 'last_preset_hero' not in st.session_state: st.session_state.last_preset_hero = "Manuelle Auswahl (Leer)"
if 'last_preset_villain' not in st.session_state: st.session_state.last_preset_villain = "Manuelle Auswahl (Leer)"

def clean_card(card_str):
    text = card_str.strip()
    if not text: return None
    if text.startswith("10"): text = "T" + text[2:]
    if len(text) != 2: return None
    return text[0].upper() + text[1].lower()

def get_matrix_hand_name(r1, r2):
    return f"{ranks[r1]}{ranks[r1]}" if r1 == r2 else (f"{ranks[r1]}{ranks[r2]}s" if r1 < r2 else f"{ranks[r2]}{ranks[r1]}o")

def parse_grid_to_combos(selected_range_dict):
    suits, combos = ['c', 'h', 'd', 's'], []
    for hand, weight in selected_range_dict.items():
        if weight <= 0.0 or len(hand) < 2: continue
        r1, r2 = hand[0].upper(), hand[1].upper()
        if len(hand) == 2:
            for i in range(len(suits)):
                for j in range(i + 1, len(suits)): combos.append(([r1 + suits[i], r2 + suits[j]], weight))
        elif hand.endswith('s'):
            for s in suits: combos.append(([r1 + s, r2 + s], weight))
        elif hand.endswith('o'):
            for s1 in suits:
                for s2 in suits:
                    if s1 != s2: combos.append(([r1 + s1, r2 + s2], weight))
    return combos

def get_clean_class_name(id): 
    return {1: "Straight Flush", 2: "Four of a Kind (Vierling)", 3: "Full House", 4: "Flush", 5: "Straight (Straße)", 6: "Three of a Kind (Drilling)", 7: "Two Pair", 8: "One Pair (Ein Paar)", 9: "High Card"}.get(id, "High Card")
def check_draws(v_combo, board_cards):
    full_7 = v_combo + board_cards
    suits = [c[1] for c in full_7 if len(c) == 2]
    values_str = "23456789TJQKA"
    val_indices = sorted(list(set([values_str.index(c[0]) for c in full_7 if len(c) == 2])))
    for s in ['c', 'h', 'd', 's']:
        if suits.count(s) == 4: return "Flush Draw"
    is_oesd, is_gutshot = False, False
    for start in range(0, 10):
        window = set(range(start, start + 5))
        if start == 9: window = {12, 0, 1, 2, 3}
        hits = len(window.intersection(val_indices))
        if hits == 4:
            if start in val_indices and (start+4) in val_indices and start != 9: is_gutshot = True
            else: is_oesd = True
    if is_oesd: return "OESD (Straight Draw)"
    if is_gutshot: return "Gutshot"
    return None

def calculate_hand_outs(cards_to_eval, board_cards):
    if len(board_cards) >= 5: return 0
    evaluator = Evaluator()
    full_deck = [v + s for v in '23456789TJQKA' for s in 'chds']
    dead_cards = set(cards_to_eval + board_cards)
    remaining_deck = [c for c in full_deck if c not in dead_cards]
    treys_hand = [Card.new(c) for c in cards_to_eval]
    board_treys = [Card.new(c) for c in board_cards]
    try: current_class = evaluator.get_rank_class(evaluator.evaluate(treys_hand, board_treys))
    except: current_class = 10
    outs_count = 0
    for next_card in remaining_deck:
        new_class = evaluator.get_rank_class(evaluator.evaluate(treys_hand, board_treys + [Card.new(next_card)]))
        if new_class < current_class and new_class <= 8: outs_count += 1
    return outs_count

def run_flexible_simulation(hero_mode, hero_input_hand, flop_input, turn_input, river_input, selected_range_hero, selected_range_villain, iterations):
    board_raw = flop_input + "," + turn_input + "," + river_input
    board_cards = [clean_card(c) for c in re.findall(r'[2-9TJQKA10][chdsCHDS]', board_raw)]
    board_cards = [c for c in board_cards if c]
    if len(board_cards) < 3: return {"error": "Bitte gib mindestens 3 Flop-Karten ein!"}
    
    evaluator = Evaluator()
    full_deck_str = [v + s for v in '23456789TJQKA' for s in 'chds']
    full_deck_treys = {c: Card.new(c) for c in full_deck_str}
    board_treys = [full_deck_treys[c] for c in board_cards]
    combos_villain = parse_grid_to_combos(selected_range_villain)
    if not combos_villain: return {"error": "Bitte wähle für den Gegner (Villain) Hände in der Matrix aus!"}

    if hero_mode == "Feste Hand (Statisch)":
        hero_static_cards = [clean_card(c) for c in re.findall(r'[2-9TJQKA10][chdsCHDS]', hero_input_hand)]
        if len(hero_static_cards) != 2: return {"error": "Bitte gib exakt 2 gültige Karten für Hero ein (z.B. AsKs)!"}
        valid_hero_combos = [(hero_static_cards, 1.0)]
        total_hero_weight = 1.0
        hero_score = evaluator.evaluate([full_deck_treys[c] for c in hero_static_cards], board_treys)
        hero_class_name = get_clean_class_name(evaluator.get_rank_class(hero_score))
        if hero_class_name in ["High Card", "One Pair (Ein Paar)"] and len(board_cards) < 5:
            hd = check_draws(hero_static_cards, board_cards)
            if hd: hero_class_name = f"{hero_class_name} + {hd}"
        hero_class_counts = {hero_class_name: 1.0}
        total_hero_outs = calculate_hand_outs(hero_static_cards, board_cards)
    else:
        combos_hero = parse_grid_to_combos(selected_range_hero)
        if not combos_hero: return {"error": "Bitte wähle für Hero Hände in der linken Matrix aus!"}
        valid_hero_combos, total_hero_weight, total_hero_outs, hero_class_counts = [], 0.0, 0.0, {}
        for combo, weight in combos_hero:
            if combo[0] not in board_cards and combo[1] not in board_cards:
                valid_hero_combos.append((combo, weight))
                total_hero_weight += weight
                total_hero_outs += (calculate_hand_outs(combo, board_cards) * weight)
                try:
                    v_treys = [full_deck_treys[combo[0]], full_deck_treys[combo[1]]]
                    c_name = get_clean_class_name(evaluator.get_rank_class(evaluator.evaluate(v_treys, board_treys)))
                    if c_name in ["High Card", "One Pair (Ein Paar)"] and len(board_cards) < 5:
                        dt = check_draws(combo, board_cards)
                        if dt: c_name = f"{c_name} + {dt}"
                    hero_class_counts[c_name] = hero_class_counts.get(c_name, 0.0) + weight
                except: continue

    villain_class_counts, valid_villain_combos, total_villain_weight, total_villain_outs = {}, [], 0.0, 0.0
    for combo, weight in combos_villain:
        if combo[0] not in board_cards and combo[1] not in board_cards:
            valid_villain_combos.append((combo, weight))
            total_villain_weight += weight
            total_villain_outs += (calculate_hand_outs(combo, board_cards) * weight)
            try:
                v_treys = [full_deck_treys[combo[0]], full_deck_treys[combo[1]]]
                c_name = get_clean_class_name(evaluator.get_rank_class(evaluator.evaluate(v_treys, board_treys)))
                if c_name in ["High Card", "One Pair (Ein Paar)"] and len(board_cards) < 5:
                    dt = check_draws(combo, board_cards)
                    if dt: c_name = f"{c_name} + {dt}"
                villain_class_counts[c_name] = villain_class_counts.get(c_name, 0.0) + weight
            except: continue
            
    if not valid_hero_combos or not valid_villain_combos: return {"error": "Eine der Auswahlen wird komplett durch das Board geblockt!"}
    
    hero_wins, needed_cards = 0.0, 5 - len(board_cards)
    hero_flat_combos, hero_flat_weights = zip(*valid_hero_combos)
    villain_flat_combos, villain_flat_weights = zip(*valid_villain_combos)
    
    p_bar = st.progress(0)
    for i in range(iterations):
        if i % max(1, (iterations // 10)) == 0: p_bar.progress(i / iterations)
        hc = random.choices(hero_flat_combos, weights=hero_flat_weights, k=1)[0]
        vc = random.choices(villain_flat_combos, weights=villain_flat_weights, k=1)[0]
        dead_sim = set(board_cards + hc + vc)
        if len(dead_sim) < len(board_cards) + 4: continue
        
        ht = [full_deck_treys[hc[0]], full_deck_treys[hc[1]]]
        vt = [full_deck_treys[vc[0]], full_deck_treys[vc[1]]]
        if needed_cards == 0:
            if evaluator.evaluate(ht, board_treys) < evaluator.evaluate(vt, board_treys): hero_wins += 1
            elif evaluator.evaluate(ht, board_treys) == evaluator.evaluate(vt, board_treys): hero_wins += 0.5
        else:
            rem_deck = [c for c in full_deck_str if c not in dead_sim]
            final_board = board_treys + [full_deck_treys[c] for c in random.sample(rem_deck, needed_cards)]
            if evaluator.evaluate(ht, final_board) < evaluator.evaluate(vt, final_board): hero_wins += 1
            elif evaluator.evaluate(ht, final_board) == evaluator.evaluate(vt, final_board): hero_wins += 0.5
            
    p_bar.progress(1.0)
    return {
        "hero_equity": (hero_wins / iterations) * 100, "villain_equity": 100 - ((hero_wins / iterations) * 100),
        "hero_class_counts": hero_class_counts, "villain_class_counts": villain_class_counts,
        "total_hero_combos": total_hero_weight, "total_villain_combos": total_villain_weight,
        "hero_outs": total_hero_outs / total_hero_weight, "villain_outs": total_villain_outs / total_villain_weight,
        "river_reached": needed_cards == 0
    }
col_sidebar, col_matrix_h, col_matrix_v = st.columns([1.1, 1.4, 1.4])

with col_sidebar:
    st.header("📥 Tisch-Situation")
    hero_mode = st.selectbox("Modus für DEINE Hand (Hero):", ["Feste Hand (Statisch)", "Preflop-Range (R v R)"])
    
    hero_input_hand = ""
    if hero_mode == "Feste Hand (Statisch)":
        hero_input_hand = st.text_input("Deine feste Hand (Hero):", value="AsKs")
    
    flop_input = st.text_input("Flop (3 Karten)", value="Ah, Th, 3d")
    turn_input = st.text_input("Turn (1 Karte)", value="")
    river_input = st.text_input("River (1 Karte)", value="")
    iterations = st.slider("Monte-Carlo Iterationen", min_value=1000, max_value=20000, value=5000, step=1000)
    st.markdown("---")
    
    if hero_mode == "Preflop-Range (R v R)":
        preset_h = st.selectbox("Preset für DEINE Range (Hero):", options=list(PRESETS.keys()), index=0)
        if preset_h != st.session_state.last_preset_hero:
            st.session_state.selected_range_hero = PRESETS[preset_h].copy()
            st.session_state.last_preset_hero = preset_h
            st.rerun()
            
    preset_v = st.selectbox("Preset für GEGNER Range (Villain):", options=list(PRESETS.keys()), index=1)
    if preset_v != st.session_state.last_preset_villain:
        st.session_state.selected_range_villain = PRESETS[preset_v].copy()
        st.session_state.last_preset_villain = preset_v
        st.rerun()

with col_matrix_h:
    if hero_mode == "Preflop-Range (R v R)":
        st.subheader("🃏 Deine Range (Hero)")
        st.markdown("<style>div[data-testid='stHorizontalBlock'] div:nth-child(2) button[data-baseweb='button'][type='primary'] { background-color: #FF4B4B !important; color: white !important; }</style>", unsafe_allow_html=True)
        for r1 in range(13):
            cols = st.columns(13)
            for r2 in range(13):
                name = get_matrix_hand_name(r1, r2)
                w = st.session_state.selected_range_hero.get(name, 0.0)
                if cols[r2].button(name, key=f"h_{name}", type="primary" if w > 0 else "secondary"):
                    if w > 0: del st.session_state.selected_range_hero[name]
                    else: st.session_state.selected_range_hero[name] = 1.0
                    st.session_state.last_preset_hero = "Manuelle Auswahl (Leer)"
                    st.rerun()
    else:
        st.info("ℹ️ Im statischen Modus gibst du deine beiden Karten einfach links im Textfeld ein.")

with col_matrix_v:
    st.subheader("🎴 Gegner-Range (Villain)")
    st.markdown("<style>div[data-testid='stHorizontalBlock'] div:nth-child(3) button[data-baseweb='button'][type='primary'] { background-color: #1F77B4 !important; color: white !important; }</style>", unsafe_allow_html=True)
    for r1 in range(13):
        cols = st.columns(13)
        for r2 in range(13):
            name = get_matrix_hand_name(r1, r2)
            w = st.session_state.selected_range_villain.get(name, 0.0)
            if cols[r2].button(name, key=f"v_{name}", type="primary" if w > 0 else "secondary"):
                if w > 0: del st.session_state.selected_range_villain[name]
                else: st.session_state.selected_range_villain[name] = 1.0
                st.session_state.last_preset_villain = "Manuelle Auswahl (Leer)"
                st.rerun()

st.markdown("---")
if st.button("🚀 Poker RWA Analyse starten", type="primary", use_container_width=True):
    res = run_flexible_simulation(hero_mode, hero_input_hand, flop_input, turn_input, river_input, st.session_state.selected_range_hero, st.session_state.selected_range_villain, iterations)
    if "error" in res: st.error(res["error"])
    else:
        st.success("Analyse beendet!")
        col_m1, col_m2 = st.columns(2)
        col_m1.metric(label="Deine Equity (Hero)", value=f"{res['hero_equity']:.2f} %")
        col_m2.metric(label="Gegner Equity (Villain)", value=f"{res['villain_equity']:.2f} %")
        
        if not res.get("river_reached", False):
            col_o1, col_o2 = st.columns(2)
            col_o1.metric(label=f"{'Deine Outs' if hero_mode=='Feste Hand (Statisch)' else 'Ø Deine Outs (Range)'}", value=f"{res['hero_outs']:.1f}" if hero_mode=='Preflop-Range (R v R)' else f"{int(res['hero_outs'])}")
            col_o2.metric(label="Ø Gegner Outs (Villain Range)", value=f"{res['villain_outs']:.1f}")
            
        equity_df = pd.DataFrame({"Spieler": ["Hero (Du)", "Villain (Gegner)"], "Equity (%)": [res['hero_equity'], res['villain_equity']]})
        st.bar_chart(data=equity_df, x="Spieler", y="Equity (%)", use_container_width=True)
        
        st.markdown("### 📊 Postflop Handstärken- & Draw-Verteilungen im Vergleich")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown(f"**🃏 {'Deine Handstärke (Hero):' if hero_mode=='Feste Hand (Statisch)' else 'Deine Verteilung (Hero Range):'}**")
            h_data = [{"Handstärke / Draw": c, "Combos": round(w, 2), "Anteil": (w / res['total_hero_combos']) * 100} for c, w in res['hero_class_counts'].items()]
            if h_data:
                df_h = pd.DataFrame(h_data).sort_values(by="Combos", ascending=False)
                st.bar_chart(data=df_h, x="Handstärke / Draw", y="Anteil", use_container_width=True)
                df_h["Anteil"] = df_h["Anteil"].map(lambda x: f"{x:.1f} %")
                st.table(df_h)
        with col_t2:
            st.markdown("**🎴 Gegnerische Verteilung (Villain Range):**")
            v_data = [{"Handstärke / Draw": c, "Combos": round(w, 2), "Anteil": (w / res['total_villain_combos']) * 100} for c, w in res['villain_class_counts'].items()]
            if v_data:
                df_v = pd.DataFrame(v_data).sort_values(by="Combos", ascending=False)
                st.bar_chart(data=df_v, x="Handstärke / Draw", y="Anteil", use_container_width=True)
                df_v["Anteil"] = df_v["Anteil"].map(lambda x: f"{x:.1f} %")
                st.table(df_v)
