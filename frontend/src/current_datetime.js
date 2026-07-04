const currentDateTime = document.querySelector("#currentDateTime");

if (currentDateTime) {
  const updateCurrentDateTime = () => {
    const now = new Date();
    currentDateTime.textContent = formatCurrentDateTime(now);
    currentDateTime.dateTime = now.toISOString();
    currentDateTime.title = `ブラウザの現在日時: ${now.toLocaleString()}`;
  };

  updateCurrentDateTime();
  window.setInterval(updateCurrentDateTime, 1000);
}

function formatCurrentDateTime(value) {
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(value);
}
