import { SUWON, WMO } from "./config";

export async function fetchWeather() {
  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${SUWON.lat}&longitude=${SUWON.lon}` +
    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code" +
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max" +
    "&forecast_days=7&timezone=Asia%2FSeoul";
  const r = await fetch(url, { signal: AbortSignal.timeout(8000) });
  if (!r.ok) throw new Error(`weather ${r.status}`);
  const d: any = await r.json();
  const look = (code: number): [string, string] => WMO[code] ?? ["🌡", `코드 ${code}`];
  const [emoji, desc] = look(Number(d.current.weather_code ?? 0));
  const dl = d.daily;
  return {
    current: {
      temp: d.current.temperature_2m, feels: d.current.apparent_temperature,
      humidity: d.current.relative_humidity_2m, wind: d.current.wind_speed_10m, emoji, desc,
    },
    forecast: (dl.time as string[]).map((date, i) => {
      const [em, dc] = look(Number(dl.weather_code[i] ?? 0));
      return {
        date, emoji: em, desc: dc, tMax: dl.temperature_2m_max[i], tMin: dl.temperature_2m_min[i],
        precip: dl.precipitation_sum[i] ?? 0, windMax: dl.wind_speed_10m_max[i] ?? 0,
      };
    }),
  };
}
