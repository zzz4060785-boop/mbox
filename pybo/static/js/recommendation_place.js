(() => {
  const queryInput = document.getElementById("kakaoPlaceQuery");
  const searchButton = document.getElementById("kakaoPlaceSearchButton");
  const message = document.getElementById("kakaoPlaceMessage");
  const results = document.getElementById("kakaoPlaceResults");
  const placeName = document.getElementById("placeName");
  const region = document.getElementById("placeRegion");
  const address = document.getElementById("placeAddress");
  const mapUrl = document.getElementById("placeMapUrl");

  if (!queryInput || !searchButton || !results) return;

  const showMessage = (text, isError = false) => {
    message.textContent = text;
    message.classList.toggle("error", isError);
  };

  const selectPlace = (place) => {
    placeName.value = place.name || "";
    region.value = place.region || "";
    address.value = place.address || "";
    mapUrl.value = place.map_url || "";
    results.hidden = true;
    showMessage(
      `${place.name}을(를) 선택했습니다.${place.phone ? ` · ${place.phone}` : ""}`
    );
    placeName.focus();
  };

  const renderPlaces = (places) => {
    results.replaceChildren();
    if (!places.length) {
      results.hidden = true;
      showMessage("검색 결과가 없습니다. 지역명을 함께 입력해 보세요.", true);
      return;
    }

    places.forEach((place) => {
      const button = document.createElement("button");
      const name = document.createElement("strong");
      const detail = document.createElement("span");
      const category = document.createElement("small");
      button.type = "button";
      button.className = "place-result";
      name.textContent = place.name;
      detail.textContent = [place.address, place.phone].filter(Boolean).join(" · ");
      category.textContent = place.category || "카카오맵 장소";
      button.append(name, detail, category);
      button.addEventListener("click", () => selectPlace(place));
      results.append(button);
    });
    results.hidden = false;
    showMessage(`${places.length}개의 장소를 찾았습니다. 하나를 선택해 주세요.`);
  };

  const searchPlaces = async () => {
    const query = queryInput.value.trim();
    if (query.length < 2) {
      showMessage("장소명을 두 글자 이상 입력해 주세요.", true);
      queryInput.focus();
      return;
    }

    searchButton.disabled = true;
    results.hidden = true;
    showMessage("카카오맵에서 장소를 찾고 있습니다.");
    try {
      const response = await fetch(
        `/api/recommendations/places?q=${encodeURIComponent(query)}`,
        { headers: { Accept: "application/json" } }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "장소 검색에 실패했습니다.");
      renderPlaces(data.places || []);
    } catch (error) {
      showMessage(error.message || "장소 검색에 실패했습니다.", true);
    } finally {
      searchButton.disabled = false;
    }
  };

  searchButton.addEventListener("click", searchPlaces);
  queryInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchPlaces();
    }
  });
})();
