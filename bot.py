def scrape_results():
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    games = soup.find_all("p", class_="livegame")
    debug_lines = []
    current_results = {}

    for game in games:
        market_raw = game.get_text(strip=True)
        result_tag = game.find_next_sibling("p", class_="liveresult")
        result_raw = result_tag.get_text(strip=True) if result_tag else "WAIT"

        debug_lines.append(f"GAME: {market_raw} | RESULT: {result_raw}")

    if not debug_lines:
        debug_lines.append("⚠️ कोई भी livegame block नहीं मिला!")

    # Debug snippet Telegram पर भेजो
    send_message("\n".join(debug_lines)[:4000])

    return current_results
