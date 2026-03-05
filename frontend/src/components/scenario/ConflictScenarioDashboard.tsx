"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  ArrowRight,
  Fuel,
  Plane,
  Radar,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useScenarioLiveMarket } from "@/lib/hooks/useScenarios";

type ScenarioKey = "contained" | "proxy" | "hormuz";

type SectorDefinition = {
  sector: string;
  baseScore: number;
  intensitySensitivity: number;
  hormuzSensitivity: number;
  timeSensitivity: number;
  firstOrder: string;
  secondOrder: string;
};

type EquityDefinition = {
  ticker: string;
  name: string;
  region: string;
  sector: string;
  scoreOffset: number;
  beta: number;
  note: string;
};

type ScenarioDefinition = {
  key: ScenarioKey;
  label: string;
  title: string;
  tone: string;
  probability: number;
  summary: string;
  posture: string;
  watchFor: string;
  diplomacy: string;
  baseOilMin: number;
  baseOilMax: number;
  oilShockBase: number;
  inflationBase: number;
  growthBase: number;
  riskBase: number;
  energyRevenueBase: number;
  persistence: number;
  sectors: SectorDefinition[];
  equities: EquityDefinition[];
};

type IndicatorDefinition = {
  name: string;
  ticker: string;
  unit: string;
  caution: number;
  stress: number;
  level: (inputs: DashboardInputs) => number;
  note: string;
};

type DashboardInputs = {
  scenario: ScenarioDefinition;
  weeks: number;
  intensity: number;
  hormuz: number;
};

const SCENARIOS: Record<ScenarioKey, ScenarioDefinition> = {
  contained: {
    key: "contained",
    label: "Scenario 1",
    title: "Contained retaliation",
    tone: "bg-emerald-500/15 text-emerald-700",
    probability: 40,
    summary:
      "Direct strikes stay limited, Iran responds in a calibrated way, and diplomacy caps the energy shock before it spreads deeply into India’s inflation and earnings setup.",
    posture: "Short-lived risk-off pulse, then a selective rebound in Indian cyclicals.",
    watchFor: "Proxy headlines without sustained tanker or insurance disruption.",
    diplomacy: "Backchannel mediation restores a narrow de-escalation lane quickly enough to anchor crude.",
    baseOilMin: 84,
    baseOilMax: 96,
    oilShockBase: 34,
    inflationBase: 28,
    growthBase: 24,
    riskBase: 32,
    energyRevenueBase: 42,
    persistence: 0.65,
    sectors: [
      {
        sector: "Upstream and integrated energy",
        baseScore: 2.4,
        intensitySensitivity: 1.6,
        hormuzSensitivity: 1.7,
        timeSensitivity: 0.7,
        firstOrder: "Higher crude realizations lift ONGC, Oil India, and Reliance earnings expectations.",
        secondOrder: "India’s energy winners start outperforming index financials and consumption quickly.",
      },
      {
        sector: "Defence PSUs",
        baseScore: 1.8,
        intensitySensitivity: 1.8,
        hormuzSensitivity: 0.7,
        timeSensitivity: 0.8,
        firstOrder: "Renewed focus on missiles, naval assets, and air defence supports HAL, BEL, BDL, and Mazagon.",
        secondOrder: "The market tends to front-run procurement headlines well before order conversion.",
      },
      {
        sector: "Airlines and travel",
        baseScore: -2.2,
        intensitySensitivity: -1.7,
        hormuzSensitivity: -2.4,
        timeSensitivity: -1.2,
        firstOrder: "Jet fuel rises faster than IndiGo and other travel names can reprice.",
        secondOrder: "Margin compression shows up before demand actually breaks.",
      },
      {
        sector: "Paints and chemicals",
        baseScore: -0.4,
        intensitySensitivity: -0.7,
        hormuzSensitivity: -0.9,
        timeSensitivity: -0.6,
        firstOrder: "Crude derivatives and feedstock inflation pressure Asian Paints, Pidilite, and chemical margins.",
        secondOrder: "This group underperforms even in mild oil shocks because input inflation is visible fast.",
      },
      {
        sector: "Consumer staples",
        baseScore: 0.8,
        intensitySensitivity: 0.2,
        hormuzSensitivity: 0.3,
        timeSensitivity: 0.5,
        firstOrder: "Defensive rotation supports HUL, ITC, and steady domestic compounders.",
        secondOrder: "Pricing power beats discretionary demand sensitivity.",
      },
      {
        sector: "Private banks and NBFCs",
        baseScore: -0.8,
        intensitySensitivity: -0.8,
        hormuzSensitivity: -1,
        timeSensitivity: -0.9,
        firstOrder: "Risk-off and tighter liquidity weigh on large lenders and market-sensitive financials.",
        secondOrder: "The drag stays limited if crude reverses before INR and rates move materially.",
      },
      {
        sector: "IT exporters",
        baseScore: 1,
        intensitySensitivity: 0.4,
        hormuzSensitivity: 0.5,
        timeSensitivity: 0.7,
        firstOrder: "Defensive earnings and a softer rupee create a partial hedge for large-cap IT.",
        secondOrder: "If US demand holds, IT can stabilize the broader index after the first shock.",
      },
      {
        sector: "Shipping and logistics",
        baseScore: 0.4,
        intensitySensitivity: 0.9,
        hormuzSensitivity: 1.6,
        timeSensitivity: 0.9,
        firstOrder: "Freight and insurance costs rise first, helping select shipping exposure while hurting import-heavy logistics.",
        secondOrder: "Moves are violent and often reverse with diplomacy headlines.",
      },
    ],
    equities: [
      { ticker: "RELIANCE", name: "Reliance Industries", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.45, beta: 1.1, note: "Most important index-level energy hedge in India." },
      { ticker: "ONGC", name: "ONGC", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.35, beta: 1.15, note: "Cleaner upstream crude beta than refiners and OMCs." },
      { ticker: "OIL", name: "Oil India", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.4, beta: 1.2, note: "Higher torque to sustained crude upside." },
      { ticker: "HAL", name: "HAL", region: "India", sector: "Defence PSUs", scoreOffset: 0.45, beta: 1.1, note: "Air defence and procurement sentiment usually bid the stock early." },
      { ticker: "BEL", name: "Bharat Electronics", region: "India", sector: "Defence PSUs", scoreOffset: 0.2, beta: 1.05, note: "Radar and electronics exposure makes it a clean India defence proxy." },
      { ticker: "INDIGO", name: "InterGlobe Aviation", region: "India", sector: "Airlines and travel", scoreOffset: -0.55, beta: 1.25, note: "Jet fuel is the cleanest India transmission channel from Brent." },
      { ticker: "ASIANPAINT", name: "Asian Paints", region: "India", sector: "Paints and chemicals", scoreOffset: -0.3, beta: 0.95, note: "Crude-linked inputs create a fast margin drag." },
      { ticker: "HDFCBANK", name: "HDFC Bank", region: "India", sector: "Private banks and NBFCs", scoreOffset: -0.15, beta: 0.9, note: "Broad India risk appetite and liquidity proxy." },
      { ticker: "TCS", name: "TCS", region: "India", sector: "IT exporters", scoreOffset: 0.15, beta: 0.85, note: "Defensive and INR-sensitive compared with domestic cyclicals." },
      { ticker: "ITC", name: "ITC", region: "India", sector: "Consumer staples", scoreOffset: 0.15, beta: 0.8, note: "Domestic defensiveness and pricing resilience help." },
    ],
  },
  proxy: {
    key: "proxy",
    label: "Scenario 2",
    title: "Proxy escalation and sanctions squeeze",
    tone: "bg-amber-500/15 text-amber-700",
    probability: 35,
    summary:
      "Proxy retaliation persists for weeks, sanctions tighten, and shipping or insurance stress stays elevated long enough to matter for India’s imported inflation and market leadership.",
    posture: "Sticky inflation scare with rolling cross-asset stress in Indian equities.",
    watchFor: "Repeated strikes on regional energy or logistics nodes and a crude market that refuses to calm down.",
    diplomacy: "Talks stay open but fail to cap proxy activity quickly enough for India importers to relax.",
    baseOilMin: 94,
    baseOilMax: 110,
    oilShockBase: 52,
    inflationBase: 44,
    growthBase: 38,
    riskBase: 48,
    energyRevenueBase: 58,
    persistence: 0.9,
    sectors: [
      {
        sector: "Upstream and integrated energy",
        baseScore: 3.3,
        intensitySensitivity: 1.5,
        hormuzSensitivity: 1.8,
        timeSensitivity: 0.9,
        firstOrder: "Crude stays high enough to keep ONGC, Oil India, and parts of Reliance structurally supported.",
        secondOrder: "This becomes a persistent leadership pocket inside the Indian market.",
      },
      {
        sector: "OMCs and refiners",
        baseScore: 2.7,
        intensitySensitivity: 1.8,
        hormuzSensitivity: 0.7,
        timeSensitivity: 1,
        firstOrder: "IOC, BPCL, and HPCL struggle if crude rises faster than retail pricing can adjust.",
        secondOrder: "Margin pain matters more than the headline revenue line in this regime.",
      },
      {
        sector: "Defence PSUs",
        baseScore: -3.1,
        intensitySensitivity: -1.4,
        hormuzSensitivity: -2.2,
        timeSensitivity: -1.4,
        firstOrder: "Persistent conflict and procurement focus support the rerating of HAL, BEL, BDL, and naval names.",
        secondOrder: "The market pays for duration of demand, not just daily headlines.",
      },
      {
        sector: "Airlines and travel",
        baseScore: -1.7,
        intensitySensitivity: -1,
        hormuzSensitivity: -0.9,
        timeSensitivity: -1,
        firstOrder: "Fuel and rerouting costs both hit earnings quality.",
        secondOrder: "Travel demand softens if inflation expectations keep drifting higher.",
      },
      {
        sector: "Private banks and NBFCs",
        baseScore: -1.1,
        intensitySensitivity: -0.8,
        hormuzSensitivity: -1.3,
        timeSensitivity: -1,
        firstOrder: "Higher oil and a weaker rupee tighten financial conditions for Indian cyclicals.",
        secondOrder: "Credit costs do not spike immediately, but leadership rotates away from lenders.",
      },
      {
        sector: "Paints and chemicals",
        baseScore: 1.2,
        intensitySensitivity: 0.4,
        hormuzSensitivity: 0.4,
        timeSensitivity: 0.7,
        firstOrder: "Feedstock and freight inflation pressure margins across paints, adhesives, and select chemicals.",
        secondOrder: "These stocks are a good second-order read on how persistent the crude shock is becoming.",
      },
      {
        sector: "Consumer staples",
        baseScore: 1.8,
        intensitySensitivity: 0.6,
        hormuzSensitivity: 0.6,
        timeSensitivity: 0.9,
        firstOrder: "Defensive domestic franchises keep attracting capital.",
        secondOrder: "Pricing power becomes a quality factor again once inflation fears rise.",
      },
      {
        sector: "Shipping and logistics",
        baseScore: 2,
        intensitySensitivity: 1.2,
        hormuzSensitivity: 2.1,
        timeSensitivity: 1.1,
        firstOrder: "Rerouting and insurance premia lift freight and operational volatility.",
        secondOrder: "Shipping-linked names can rally hard, but they remain headline-sensitive.",
      },
    ],
    equities: [
      { ticker: "RELIANCE", name: "Reliance Industries", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.55, beta: 1.12, note: "India’s most important energy-and-index hedge in a prolonged crude squeeze." },
      { ticker: "ONGC", name: "ONGC", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.6, beta: 1.18, note: "High sensitivity to a sustained crude squeeze." },
      { ticker: "OIL", name: "Oil India", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.7, beta: 1.22, note: "More torque than large caps if crude stays elevated." },
      { ticker: "IOC", name: "Indian Oil", region: "India", sector: "OMCs and refiners", scoreOffset: -0.45, beta: 1, note: "Retail pricing and refining margins both matter under sticky crude." },
      { ticker: "BPCL", name: "BPCL", region: "India", sector: "OMCs and refiners", scoreOffset: -0.4, beta: 1.02, note: "Cleaner downside expression when crude stays high for weeks." },
      { ticker: "HAL", name: "HAL", region: "India", sector: "Defence PSUs", scoreOffset: 0.55, beta: 1.08, note: "Longer-duration conflict keeps defence order books in focus." },
      { ticker: "BEL", name: "Bharat Electronics", region: "India", sector: "Defence PSUs", scoreOffset: 0.3, beta: 1.04, note: "Air-defence and electronics narrative deepens in persistent conflict." },
      { ticker: "INDIGO", name: "InterGlobe Aviation", region: "India", sector: "Airlines and travel", scoreOffset: -0.7, beta: 1.28, note: "Fuel and route stress both hit earnings quality." },
      { ticker: "HDFCBANK", name: "HDFC Bank", region: "India", sector: "Private banks and NBFCs", scoreOffset: -0.25, beta: 0.92, note: "A clean gauge of whether the shock is broadening into India financials." },
      { ticker: "ASIANPAINT", name: "Asian Paints", region: "India", sector: "Paints and chemicals", scoreOffset: -0.35, beta: 0.96, note: "Useful second-order inflation and feedstock read." },
      { ticker: "ITC", name: "ITC", region: "India", sector: "Consumer staples", scoreOffset: 0.15, beta: 0.82, note: "Domestic defensive profile improves versus cyclicals." },
      { ticker: "SCI", name: "Shipping Corp", region: "India", sector: "Shipping and logistics", scoreOffset: 0.4, beta: 1.18, note: "Direct freight sensitivity if routing stress persists." },
    ],
  },
  hormuz: {
    key: "hormuz",
    label: "Scenario 3",
    title: "Hormuz disruption and sustained energy shock",
    tone: "bg-rose-500/15 text-rose-700",
    probability: 25,
    summary:
      "Physical disruption or repeated threats around the Strait of Hormuz materially impair flows and push India into a clear imported-energy shock regime.",
    posture: "Indian stagflation scare with broad derating outside energy and defence.",
    watchFor: "Confirmed tanker delays, insurance withdrawals, or repeated hits to export infrastructure.",
    diplomacy: "Talks matter less than proof that the shipping lane and export terminals are functioning normally.",
    baseOilMin: 112,
    baseOilMax: 138,
    oilShockBase: 72,
    inflationBase: 64,
    growthBase: 56,
    riskBase: 70,
    energyRevenueBase: 76,
    persistence: 1.25,
    sectors: [
      {
        sector: "Upstream and integrated energy",
        baseScore: 4.1,
        intensitySensitivity: 1.2,
        hormuzSensitivity: 2,
        timeSensitivity: 1,
        firstOrder: "Spot crude spikes hard and India’s upstream energy names rerate immediately.",
        secondOrder: "Balance-sheet optionality and special payouts become central to the trade.",
      },
      {
        sector: "OMCs and refiners",
        baseScore: 3.5,
        intensitySensitivity: 1.5,
        hormuzSensitivity: 0.8,
        timeSensitivity: 1.1,
        firstOrder: "OMC margins come under severe pressure if crude spikes and retail pricing lags.",
        secondOrder: "This becomes one of the most important negative second-order equity channels in India.",
      },
      {
        sector: "Defence PSUs",
        baseScore: -4.2,
        intensitySensitivity: -1.1,
        hormuzSensitivity: -2.6,
        timeSensitivity: -1.5,
        firstOrder: "Sustained conflict drives procurement urgency and supports defence rerating.",
        secondOrder: "Naval and air-defence exposure should outperform general industrial PSUs.",
      },
      {
        sector: "Airlines and travel",
        baseScore: -2.4,
        intensitySensitivity: -1.1,
        hormuzSensitivity: -1,
        timeSensitivity: -1.1,
        firstOrder: "Jet fuel and route disruption severely pressure earnings.",
        secondOrder: "Demand destruction becomes a bigger problem than pass-through.",
      },
      {
        sector: "Private banks and NBFCs",
        baseScore: -2.8,
        intensitySensitivity: -0.9,
        hormuzSensitivity: -1.5,
        timeSensitivity: -1.2,
        firstOrder: "Credit spreads widen, liquidity tightens, and broad India cyclicals derisk.",
        secondOrder: "Banks remain large index weights, so this matters for benchmark downside.",
      },
      {
        sector: "Consumer discretionary",
        baseScore: -2.1,
        intensitySensitivity: -1,
        hormuzSensitivity: -1.3,
        timeSensitivity: -1.2,
        firstOrder: "Real income squeeze hits autos, retail, and travel-linked consumption.",
        secondOrder: "Autos and travel underperform staples and utilities sharply.",
      },
      {
        sector: "IT exporters",
        baseScore: 2.4,
        intensitySensitivity: 0.5,
        hormuzSensitivity: 0.8,
        timeSensitivity: 1,
        firstOrder: "The rupee can cushion IT earnings, but global growth fears limit the upside.",
        secondOrder: "IT becomes relative shelter, not a pure bullish expression.",
      },
      {
        sector: "Utilities and power",
        baseScore: 2.8,
        intensitySensitivity: 1.1,
        hormuzSensitivity: 2.7,
        timeSensitivity: 1.2,
        firstOrder: "Domestic defensive cash flows attract capital as growth-sensitive sectors derate.",
        secondOrder: "Power names with less imported fuel pressure should hold up best.",
      },
      {
        sector: "Shipping and logistics",
        baseScore: 2.4,
        intensitySensitivity: 1.1,
        hormuzSensitivity: 2.7,
        timeSensitivity: 1.2,
        firstOrder: "Freight markets gap higher as routing and insurance tighten.",
        secondOrder: "Spot beneficiaries remain volatile, but logistics stress confirms the tail scenario.",
      },
    ],
    equities: [
      { ticker: "RELIANCE", name: "Reliance Industries", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.65, beta: 1.14, note: "Direct Indian beneficiary of a sustained oil and energy shock." },
      { ticker: "ONGC", name: "ONGC", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.75, beta: 1.18, note: "One of the clearest India longs in the tail scenario." },
      { ticker: "OIL", name: "Oil India", region: "India", sector: "Upstream and integrated energy", scoreOffset: 0.8, beta: 1.24, note: "Highest torque among liquid India upstream names." },
      { ticker: "IOC", name: "Indian Oil", region: "India", sector: "OMCs and refiners", scoreOffset: -0.6, beta: 1.02, note: "Cleaner short expression if crude spikes and policy lags." },
      { ticker: "BPCL", name: "BPCL", region: "India", sector: "OMCs and refiners", scoreOffset: -0.55, beta: 1.03, note: "Retail fuel margin pressure dominates in the tail case." },
      { ticker: "HAL", name: "HAL", region: "India", sector: "Defence PSUs", scoreOffset: 0.6, beta: 1.08, note: "Defence duration trade strengthens sharply." },
      { ticker: "BEL", name: "Bharat Electronics", region: "India", sector: "Defence PSUs", scoreOffset: 0.4, beta: 1.04, note: "Missile and air-defence focus should dominate." },
      { ticker: "INDIGO", name: "InterGlobe Aviation", region: "India", sector: "Airlines and travel", scoreOffset: -0.85, beta: 1.35, note: "One of the cleanest India shorts against a jet fuel spike." },
      { ticker: "MARUTI", name: "Maruti Suzuki", region: "India", sector: "Consumer discretionary", scoreOffset: -0.35, beta: 0.96, note: "Real income squeeze and risk-off both matter." },
      { ticker: "TCS", name: "TCS", region: "India", sector: "IT exporters", scoreOffset: 0.1, beta: 0.84, note: "Relative shelter rather than a high-conviction bullish expression." },
      { ticker: "NTPC", name: "NTPC", region: "India", sector: "Utilities and power", scoreOffset: 0.2, beta: 0.82, note: "Defensive domestic cash flow profile helps versus cyclicals." },
      { ticker: "SCI", name: "Shipping Corp", region: "India", sector: "Shipping and logistics", scoreOffset: 0.45, beta: 1.22, note: "Freight torque can be strong, but expect volatility." },
    ],
  },
};

const INDICATORS: IndicatorDefinition[] = [
  {
    name: "VIX",
    ticker: "VIX",
    unit: "",
    caution: 24,
    stress: 32,
    level: ({ scenario, intensity, hormuz, weeks }) =>
      17 + scenario.riskBase * 0.18 + intensity * 0.05 + hormuz * 0.07 + weeks * 0.7,
    note: "Confirms whether the macro shock is spreading beyond energy and travel.",
  },
  {
    name: "MOVE",
    ticker: "MOVE",
    unit: "",
    caution: 120,
    stress: 140,
    level: ({ scenario, intensity, hormuz, weeks }) =>
      101 + scenario.inflationBase * 0.38 + intensity * 0.12 + hormuz * 0.08 + weeks * 1.5,
    note: "Rates vol tells you when inflation shock starts to tighten financial conditions.",
  },
  {
    name: "US 5Y Breakeven",
    ticker: "USGGBE05",
    unit: "%",
    caution: 2.65,
    stress: 2.95,
    level: ({ scenario, intensity, hormuz, weeks }) =>
      2.18 + scenario.inflationBase * 0.005 + intensity * 0.0032 + hormuz * 0.0026 + weeks * 0.03,
    note: "Inflation expectations are the bridge from oil to equity multiple compression.",
  },
  {
    name: "HY OAS",
    ticker: "CDX/HY",
    unit: "bp",
    caution: 420,
    stress: 520,
    level: ({ scenario, intensity, hormuz, weeks }) =>
      335 + scenario.riskBase * 1.4 + intensity * 0.7 + hormuz * 0.9 + weeks * 7,
    note: "Credit spread widening tells you when the shock is moving from sentiment to financing.",
  },
  {
    name: "DXY",
    ticker: "DXY",
    unit: "",
    caution: 105,
    stress: 107,
    level: ({ scenario, intensity, hormuz, weeks }) =>
      102.1 + scenario.riskBase * 0.03 + intensity * 0.015 + hormuz * 0.018 + weeks * 0.15,
    note: "A stronger dollar amplifies stress for energy importers and EM equities.",
  },
  {
    name: "Brent front month",
    ticker: "BRN1",
    unit: "$",
    caution: 95,
    stress: 110,
    level: ({ scenario, intensity, hormuz, weeks }) => getOilRange(scenario, weeks, intensity, hormuz).mid,
    note: "Primary first-order shock variable and the core driver of cross-asset transmission.",
  },
  {
    name: "Gold",
    ticker: "XAU",
    unit: "$",
    caution: 2520,
    stress: 2680,
    level: ({ scenario, intensity, hormuz, weeks }) =>
      2340 + scenario.riskBase * 2.4 + intensity * 1.5 + hormuz * 1.3 + weeks * 11,
    note: "Safe-haven demand and stagflation hedging rise together here.",
  },
  {
    name: "VLCC day rate",
    ticker: "TD3C",
    unit: "$k",
    caution: 55,
    stress: 90,
    level: ({ scenario, intensity, hormuz, weeks }) =>
      30 + scenario.oilShockBase * 0.18 + intensity * 0.14 + hormuz * 0.36 + weeks * 2,
    note: "Pure read-through on physical disruption, rerouting, and insurance strain.",
  },
];

const REGIONAL_MARKETS = [
  { name: "NIFTY 50", sensitivity: -1, note: "Reliance and defence can cushion, but banks and consumption still dominate the benchmark." },
  { name: "Bank Nifty", sensitivity: -1.15, note: "Liquidity, rupee pressure, and risk appetite create the main drag here." },
  { name: "India consumption", sensitivity: -1.2, note: "Autos, retail, and travel absorb the imported inflation shock fastest." },
  { name: "India defence basket", sensitivity: 1.1, note: "Procurement narrative and strategic sentiment support relative strength." },
  { name: "India energy complex", sensitivity: 0.9, note: "Upstream wins can offset OMC pain, but leadership rotates sharply inside the sector." },
  { name: "Gulf exporters", sensitivity: 0.7, note: "Energy export leverage helps, though shipping disruption can still create broad volatility." },
];

const FLOW_STEPS = [
  { title: "Hormuz disruption", key: "hormuz", icon: ShieldAlert },
  { title: "Freight and insurance", key: "freight", icon: Radar },
  { title: "Oil and products", key: "oil", icon: Fuel },
  { title: "Airline fuel costs", key: "airline", icon: Plane },
  { title: "Inflation risk", key: "inflation", icon: AlertTriangle },
  { title: "Energy revenue", key: "energy", icon: TrendingUp },
];

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function formatSigned(value: number, suffix = "%") {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
}

function scoreClass(score: number) {
  if (score >= 2.5) return "text-emerald-700";
  if (score > 0) return "text-emerald-600";
  if (score <= -2.5) return "text-rose-700";
  if (score < 0) return "text-rose-600";
  return "text-slate-600";
}

function fillColor(score: number) {
  if (score >= 2.5) return "#047857";
  if (score > 0) return "#10b981";
  if (score <= -2.5) return "#be123c";
  if (score < 0) return "#fb7185";
  return "#94a3b8";
}

function riskBand(value: number) {
  if (value >= 80) return "Extreme";
  if (value >= 60) return "High";
  if (value >= 40) return "Elevated";
  return "Contained";
}

function indicatorTone(level: number, caution: number, stress: number) {
  if (level >= stress) {
    return "bg-rose-500/10 text-rose-700 ring-rose-200";
  }
  if (level >= caution) {
    return "bg-amber-500/10 text-amber-700 ring-amber-200";
  }
  return "bg-emerald-500/10 text-emerald-700 ring-emerald-200";
}

function formatLiveValue(quote: ScenarioLiveQuote) {
  if (quote.last == null) return "Unavailable";
  const prefix = quote.currency ? `${quote.currency === "USD" ? "$" : "₹"}` : "";
  return `${prefix}${quote.last.toLocaleString("en-IN", {
    maximumFractionDigits: quote.last > 1000 ? 0 : 2,
  })}${quote.unit}`;
}

function formatLiveChange(change: number | null | undefined) {
  if (change == null) return "N/A";
  return `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
}

function changeTone(change: number | null | undefined) {
  if (change == null) return "text-slate-500";
  return change >= 0 ? "text-emerald-700" : "text-rose-700";
}

function quoteAlertTone(quote: ScenarioLiveQuote) {
  if (!quote.success || quote.last == null) return "border-slate-200 bg-slate-50";
  if (quote.id === "brent") {
    if (quote.last >= 110) return "border-rose-200 bg-rose-50";
    if (quote.last >= 95) return "border-amber-200 bg-amber-50";
  }
  if (quote.id === "indiavix") {
    if (quote.last >= 20) return "border-rose-200 bg-rose-50";
    if (quote.last >= 16) return "border-amber-200 bg-amber-50";
  }
  if (quote.id === "usdinr") {
    if (quote.last >= 84.3) return "border-rose-200 bg-rose-50";
    if (quote.last >= 83.8) return "border-amber-200 bg-amber-50";
  }
  if (quote.id === "vix") {
    if (quote.last >= 30) return "border-rose-200 bg-rose-50";
    if (quote.last >= 22) return "border-amber-200 bg-amber-50";
  }
  return "border-slate-200 bg-white";
}

function getOilRange(scenario: ScenarioDefinition, weeks: number, intensity: number, hormuz: number) {
  const midpoint =
    (scenario.baseOilMin + scenario.baseOilMax) / 2 +
    intensity * 0.17 +
    hormuz * 0.24 +
    weeks * 1.45 * scenario.persistence;
  const halfRange = 4.5 + intensity * 0.045 + hormuz * 0.055 + scenario.persistence * 2.5;
  const min = clamp(midpoint - halfRange, 72, 190);
  const max = clamp(midpoint + halfRange, min + 4, 220);
  return { min, max, mid: (min + max) / 2 };
}

function getRiskMetrics(inputs: DashboardInputs) {
  const { scenario, weeks, intensity, hormuz } = inputs;
  const oil = getOilRange(scenario, weeks, intensity, hormuz);

  return {
    oil,
    oilShock: clamp(scenario.oilShockBase + intensity * 0.42 + hormuz * 0.54 + weeks * 2.3, 0, 100),
    inflation: clamp(scenario.inflationBase + intensity * 0.28 + hormuz * 0.34 + weeks * 2.9, 0, 100),
    growth: clamp(scenario.growthBase + intensity * 0.23 + hormuz * 0.24 + weeks * 3.4, 0, 100),
    equityStress: clamp(scenario.riskBase + intensity * 0.32 + hormuz * 0.4 + weeks * 2.2, 0, 100),
    energyRevenue: clamp(
      scenario.energyRevenueBase + (oil.mid - 85) * 0.85 + intensity * 0.08 + weeks * 1.7,
      0,
      100
    ),
  };
}

function getSectorScore(
  sector: SectorDefinition,
  scenario: ScenarioDefinition,
  weeks: number,
  intensity: number,
  hormuz: number
) {
  const weekFactor = (weeks - 1) / 5;
  return clamp(
    sector.baseScore +
      (intensity / 100) * sector.intensitySensitivity * 2.2 +
      (hormuz / 100) * sector.hormuzSensitivity * 2.6 +
      weekFactor * sector.timeSensitivity * 1.8 +
      (scenario.persistence - 0.8) * 0.7,
    -5,
    5
  );
}

function getEquityRange(
  equity: EquityDefinition,
  sectorScore: number,
  weeks: number,
  intensity: number,
  hormuz: number
) {
  const center = (sectorScore + equity.scoreOffset) * (1.45 + weeks * 0.16) * equity.beta;
  const width = 1.6 + Math.abs(center) * 0.32 + intensity * 0.015 + hormuz * 0.018;
  return {
    min: clamp(center - width, -28, 28),
    max: clamp(center + width, -28, 28),
    center,
  };
}

function getCommodityCards(inputs: DashboardInputs) {
  const metrics = getRiskMetrics(inputs);
  const { scenario, weeks, intensity, hormuz } = inputs;

  const goldMid = 2340 + scenario.riskBase * 2.4 + intensity * 1.5 + hormuz * 1.3 + weeks * 11;
  const ttfMid = 34 + scenario.oilShockBase * 0.22 + intensity * 0.16 + hormuz * 0.12 + weeks * 1.9;
  const copperMid = 4.65 - scenario.growthBase * 0.006 - intensity * 0.003 - hormuz * 0.0025 - weeks * 0.025;
  const tankerMid = 30 + scenario.oilShockBase * 0.18 + intensity * 0.14 + hormuz * 0.36 + weeks * 2;
  const jetFuelMid = 24 + metrics.oilShock * 0.24 + weeks * 0.6;

  return [
    {
      name: "Brent",
      range: `$${metrics.oil.min.toFixed(0)}-$${metrics.oil.max.toFixed(0)}/bbl`,
      tone: "text-rose-700",
      note: "Core first-order shock variable.",
    },
    {
      name: "WTI",
      range: `$${(metrics.oil.min - 5).toFixed(0)}-$${(metrics.oil.max - 4).toFixed(0)}/bbl`,
      tone: "text-rose-700",
      note: "Typically trades at a discount to Brent in this setup.",
    },
    {
      name: "Gold",
      range: `$${(goldMid - 45).toFixed(0)}-$${(goldMid + 45).toFixed(0)}/oz`,
      tone: "text-amber-700",
      note: "Safe-haven plus stagflation hedge.",
    },
    {
      name: "TTF gas",
      range: `EUR ${(ttfMid - 4).toFixed(0)}-${(ttfMid + 4).toFixed(0)}/MWh`,
      tone: "text-orange-700",
      note: "Watch for Europe-specific follow-through from LNG stress.",
    },
    {
      name: "Jet fuel crack",
      range: `$${(jetFuelMid - 4).toFixed(0)}-$${(jetFuelMid + 4).toFixed(0)}/bbl`,
      tone: "text-rose-700",
      note: "Useful second-order read for airlines and freight.",
    },
    {
      name: "Copper",
      range: `$${(copperMid - 0.18).toFixed(2)}-$${(copperMid + 0.18).toFixed(2)}/lb`,
      tone: "text-sky-700",
      note: "Growth-sensitive counterweight to the oil spike.",
    },
    {
      name: "VLCC day rate",
      range: `$${(tankerMid - 6).toFixed(0)}k-$${(tankerMid + 6).toFixed(0)}k/day`,
      tone: "text-indigo-700",
      note: "Tracks the physical severity of routing stress.",
    },
  ];
}

function getRegionalView(inputs: DashboardInputs) {
  const metrics = getRiskMetrics(inputs);
  const stress = (metrics.equityStress - 50) / 15;

  return REGIONAL_MARKETS.map((region) => {
    const move = clamp(region.sensitivity * stress + (metrics.oil.mid - 95) * -0.035, -12, 12);
    return {
      ...region,
      move,
      regime:
        move >= 1.5 ? "Outperform" : move <= -3 ? "Underperform" : move <= -1 ? "Lag" : "Mixed",
    };
  });
}

function getTransmission(inputs: DashboardInputs) {
  const metrics = getRiskMetrics(inputs);

  return {
    hormuz: clamp(inputs.hormuz + inputs.scenario.persistence * 12 + inputs.weeks * 2.5, 0, 100),
    freight: clamp(metrics.oilShock + inputs.hormuz * 0.2 - 8, 0, 100),
    oil: clamp(metrics.oil.mid - 80, 0, 100),
    airline: clamp(metrics.oilShock + inputs.weeks * 3 - 6, 0, 100),
    inflation: clamp(metrics.inflation + inputs.weeks * 1.2, 0, 100),
    energy: clamp(metrics.energyRevenue, 0, 100),
  };
}

export default function ConflictScenarioDashboard() {
  const [selectedScenario, setSelectedScenario] = useState<ScenarioKey>("proxy");
  const [weeks, setWeeks] = useState(3);
  const [intensity, setIntensity] = useState(62);
  const [hormuz, setHormuz] = useState(48);
  const [chartsReady, setChartsReady] = useState(false);
  const { data: liveMarket, isLoading: liveLoading, isError: liveError } = useScenarioLiveMarket();

  useEffect(() => {
    setChartsReady(true);
  }, []);

  const scenario = SCENARIOS[selectedScenario];
  const inputs = { scenario, weeks, intensity, hormuz };
  const metrics = getRiskMetrics(inputs);
  const oilTimeline = Array.from({ length: 6 }, (_, index) => {
    const oil = getOilRange(scenario, index + 1, intensity, hormuz);
    return {
      week: `W${index + 1}`,
      low: Number(oil.min.toFixed(1)),
      high: Number(oil.max.toFixed(1)),
      mid: Number(oil.mid.toFixed(1)),
    };
  });

  const sectorRows = scenario.sectors
    .map((sector) => ({
      ...sector,
      score: Number(getSectorScore(sector, scenario, weeks, intensity, hormuz).toFixed(2)),
    }))
    .sort((a, b) => b.score - a.score);

  const sectorLookup = Object.fromEntries(sectorRows.map((sector) => [sector.sector, sector.score]));
  const liveQuoteBySymbol = new Map(
    Object.values(liveMarket?.sections ?? {})
      .flat()
      .map((quote) => [quote.symbol, quote])
  );

  const equityRows = scenario.equities
    .map((equity) => {
      const range = getEquityRange(
        equity,
        sectorLookup[equity.sector] ?? 0,
        weeks,
        intensity,
        hormuz
      );

      return {
        ...equity,
        ...range,
        liveQuote: liveQuoteBySymbol.get(equity.ticker),
      };
    })
    .sort((a, b) => Math.abs(b.center) - Math.abs(a.center));

  const commodities = getCommodityCards(inputs);
  const regionalRows = getRegionalView(inputs);
  const transmission = getTransmission(inputs);
  const indiaMarketQuotes = liveMarket?.sections.india_market ?? [];
  const globalRiskQuotes = liveMarket?.sections.global_risk ?? [];
  const liveEquityQuotes = liveMarket?.sections.india_equities ?? [];
  const indicators = INDICATORS.map((indicator) => {
    const level = Number(indicator.level(inputs).toFixed(indicator.unit === "%" ? 2 : 1));
    return {
      ...indicator,
      level,
      state: level >= indicator.stress ? "Stress" : level >= indicator.caution ? "Caution" : "Normal",
    };
  });

  const signalStack = [
    {
      title: "De-escalation confirms",
      items: [
        "No fresh hits on export infrastructure or shipping for 72-96 hours.",
        "Brent slips back below the scenario mid-range while USD/INR and India VIX cool.",
        "IndiGo, banks, and paints stop lagging ONGC and Reliance on a relative basis.",
      ],
    },
    {
      title: "Escalation confirms",
      items: [
        "Tanker insurance, rerouting, or port throughput worsen despite diplomacy headlines.",
        "Brent stays firm while USD/INR, India VIX, and Indian OMC underperformance all worsen together.",
        "Rates vol, breakevens, and the dollar rise with crude: that is the imported-stagflation tell for India.",
      ],
    },
    {
      title: "Trading focus",
      items: [
        "Pair upstream energy and defence PSUs against airlines, OMCs, paints, and travel-sensitive consumption.",
        "Watch NIFTY 50 through the RELIANCE-ONGC-HDFCBANK-INDIGO leadership mix rather than index headlines alone.",
        "If disruption fades quickly, rotate from oil hedges into banks, discretionary, and mean-reversion longs.",
      ],
    },
  ];

  return (
    <div className="space-y-6 pb-10">
      <section className="relative overflow-hidden rounded-[28px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(249,115,22,0.18),_transparent_26%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.14),_transparent_22%),linear-gradient(135deg,_#0f172a,_#111827_46%,_#1f2937)] p-6 text-white shadow-xl">
        <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px)] [background-size:28px_28px]" />
        <div className="relative space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-white/10 text-white hover:bg-white/10">Geopolitical Scenario Lab</Badge>
            <Badge className="bg-orange-500/15 text-orange-100 hover:bg-orange-500/15">2-6 week horizon</Badge>
            <Badge className="bg-sky-500/15 text-sky-100 hover:bg-sky-500/15">Cross-asset transmission</Badge>
          </div>
          <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
            <div className="space-y-3">
              <div>
                <p className="text-sm uppercase tracking-[0.28em] text-slate-300">India geopolitical dashboard</p>
                <h1 className="mt-2 max-w-3xl text-3xl font-semibold leading-tight sm:text-4xl">
                  Interactive India-first scenario dashboard for oil shock, second-order NSE impacts, and cross-asset confirmation.
                </h1>
              </div>
              <p className="max-w-3xl text-sm text-slate-300 sm:text-base">
                Frame the path of the conflict, translate it into Brent, INR, sector, and stock ranges, and monitor whether Indian equities are moving from a headline shock into a broader imported-stagflation regime.
              </p>
            </div>
            <div className="grid gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm sm:grid-cols-2">
              <HeroStat label="Scenario probability" value={`${scenario.probability}%`} note={scenario.title} />
              <HeroStat label="Brent range" value={`$${metrics.oil.min.toFixed(0)}-$${metrics.oil.max.toFixed(0)}`} note={`Week ${weeks}`} />
              <HeroStat label="Equity stress" value={riskBand(metrics.equityStress)} note={`${metrics.equityStress.toFixed(0)}/100`} />
              <HeroStat label="Primary posture" value={scenario.posture} note={scenario.watchFor} compact />
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-xl">Scenario paths</CardTitle>
            <CardDescription>
              Pick the conflict path first. The controls below then stretch or compress the oil shock and second-order transmission.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            {Object.values(SCENARIOS).map((item) => {
              const active = item.key === selectedScenario;
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setSelectedScenario(item.key)}
                  className={cn(
                    "rounded-2xl border p-4 text-left transition-all",
                    active
                      ? "border-slate-900 bg-slate-900 text-white shadow-lg"
                      : "border-slate-200 bg-white hover:border-slate-400 hover:bg-slate-50"
                  )}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", active ? "bg-white/10 text-white" : item.tone)}>
                      {item.label}
                    </span>
                    <span className={cn("text-xs", active ? "text-slate-300" : "text-muted-foreground")}>
                      {item.probability}% base case
                    </span>
                  </div>
                  <h2 className="mt-3 text-lg font-semibold">{item.title}</h2>
                  <p className={cn("mt-2 text-sm", active ? "text-slate-300" : "text-muted-foreground")}>
                    {item.summary}
                  </p>
                  <div className={cn("mt-4 text-xs", active ? "text-slate-400" : "text-slate-500")}>
                    <p>{item.posture}</p>
                    <p className="mt-1">Diplomacy: {item.diplomacy}</p>
                  </div>
                </button>
              );
            })}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-[linear-gradient(180deg,_rgba(248,250,252,1),_rgba(241,245,249,0.7))]">
          <CardHeader>
            <CardTitle className="text-xl">Control surface</CardTitle>
            <CardDescription>
              Tune the horizon, conflict intensity, and Hormuz severity to stress test the ranges.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <ControlRow label="Analysis horizon" value={`${weeks} weeks`}>
              <Slider min={1} max={6} step={1} value={[weeks]} onValueChange={(value) => setWeeks(value[0] ?? 1)} />
            </ControlRow>
            <ControlRow label="Conflict intensity" value={`${intensity}/100`}>
              <Slider
                min={0}
                max={100}
                step={1}
                value={[intensity]}
                onValueChange={(value) => setIntensity(value[0] ?? 0)}
              />
            </ControlRow>
            <ControlRow label="Hormuz disruption" value={`${hormuz}/100`}>
              <Slider min={0} max={100} step={1} value={[hormuz]} onValueChange={(value) => setHormuz(value[0] ?? 0)} />
            </ControlRow>

            <div className="grid gap-3 sm:grid-cols-2">
              <MiniStat
                title="Conflict tone"
                value={scenario.posture}
                note={scenario.watchFor}
              />
              <MiniStat
                title="Diplomatic lane"
                value={scenario.diplomacy}
                note="This mostly changes how long the market stays in shock mode."
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-xl">Live India market snapshot</CardTitle>
            <CardDescription>
              Client-side live tape from the backend API. This is the real-world confirmation layer for the scenario model.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                {liveMarket
                  ? `Last refresh ${new Date(liveMarket.fetched_at).toLocaleString("en-IN", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}`
                  : liveLoading
                    ? "Refreshing live market snapshot..."
                    : "Live market snapshot unavailable"}
              </p>
              {liveMarket && (
                <Badge variant="secondary">Cache {Math.round(liveMarket.cache_ttl_seconds / 60)} min</Badge>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {indiaMarketQuotes.map((quote) => (
                <div key={quote.id} className={cn("rounded-2xl border p-4", quoteAlertTone(quote))}>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{quote.name}</p>
                  <p className="mt-2 text-lg font-semibold text-slate-950">{formatLiveValue(quote)}</p>
                  <p className={cn("mt-2 text-sm font-medium", changeTone(quote.change_percent))}>
                    {formatLiveChange(quote.change_percent)}
                  </p>
                </div>
              ))}
            </div>
            {liveError && (
              <p className="text-sm text-rose-700">
                The live market feed failed. The modeled scenario engine still works, but the tape is not updating.
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-[linear-gradient(180deg,_rgba(255,247,237,0.7),_rgba(255,255,255,1))]">
          <CardHeader>
            <CardTitle className="text-xl">Live confirmation board</CardTitle>
            <CardDescription>
              Watch these NSE names and global risk proxies together. The signal gets stronger when they confirm the same story.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              {liveEquityQuotes.slice(0, 6).map((quote) => (
                <div key={quote.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold">{quote.name}</p>
                      <p className="text-sm text-muted-foreground">{quote.category}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-slate-950">{formatLiveValue(quote)}</p>
                      <p className={cn("text-sm font-medium", changeTone(quote.change_percent))}>
                        {formatLiveChange(quote.change_percent)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="font-semibold">Watchpoints</p>
              <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                {(liveMarket?.watchpoints ?? []).map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              {!liveMarket && !liveLoading && (
                <p className="mt-3 text-sm text-muted-foreground">
                  Once the backend responds, this panel will summarize the live India macro stress state automatically.
                </p>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {globalRiskQuotes.map((quote) => (
                <MiniStat
                  key={quote.id}
                  title={quote.name}
                  value={formatLiveValue(quote)}
                  note={formatLiveChange(quote.change_percent)}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          title="Brent range"
          value={`$${metrics.oil.min.toFixed(0)}-$${metrics.oil.max.toFixed(0)}/bbl`}
          footnote="Illustrative next-weeks trading band"
          tone="from-rose-500/20 to-orange-500/10"
        />
        <MetricCard
          title="Oil shock"
          value={`${metrics.oilShock.toFixed(0)}/100`}
          footnote={riskBand(metrics.oilShock)}
          tone="from-rose-500/20 to-rose-500/5"
        />
        <MetricCard
          title="Inflation pulse"
          value={`${metrics.inflation.toFixed(0)}/100`}
          footnote="5Y breakeven and consumer squeeze risk"
          tone="from-amber-500/20 to-orange-500/5"
        />
        <MetricCard
          title="Growth drag"
          value={`${metrics.growth.toFixed(0)}/100`}
          footnote="Cyclicals and importers weaken first"
          tone="from-sky-500/20 to-cyan-500/5"
        />
        <MetricCard
          title="Energy cash flow"
          value={`${metrics.energyRevenue.toFixed(0)}/100`}
          footnote="Integrated oils gain operating leverage"
          tone="from-emerald-500/20 to-teal-500/5"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-xl">Oil path by week</CardTitle>
            <CardDescription>
              Scenario-derived range for Brent over the next six weeks at the current control settings.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="h-[320px]">
              {chartsReady ? (
                <ResponsiveContainer width="100%" height="100%" minWidth={280} minHeight={320}>
                  <LineChart data={oilTimeline} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="week" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} domain={["dataMin - 4", "dataMax + 4"]} />
                    <Tooltip
                      formatter={(value) => [`$${Number(value ?? 0).toFixed(1)}/bbl`, ""]}
                      labelFormatter={(label) => `Horizon ${label}`}
                    />
                    <Line type="monotone" dataKey="low" stroke="#fb7185" strokeWidth={2.5} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="mid" stroke="#111827" strokeWidth={2.5} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="high" stroke="#f97316" strokeWidth={2.5} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full rounded-2xl border border-dashed border-slate-200 bg-slate-50" />
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <MiniStat title="Selected week low" value={`$${oilTimeline[weeks - 1].low}`} note="Lower bound if disruption eases." />
              <MiniStat title="Selected week mid" value={`$${oilTimeline[weeks - 1].mid}`} note="Working scenario anchor for analysis." />
              <MiniStat title="Selected week high" value={`$${oilTimeline[weeks - 1].high}`} note="Upper tail if market keeps repricing stress." />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-slate-950 text-white">
          <CardHeader>
            <CardTitle className="text-xl">Commodity ranges</CardTitle>
            <CardDescription className="text-slate-400">
              Keep the first-order commodity map beside the India equity dashboard. These are modeled short-dated bands, not live quotes.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {commodities.map((commodity) => (
              <div key={commodity.name} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{commodity.name}</p>
                <p className={cn("mt-2 text-lg font-semibold", commodity.tone)}>{commodity.range}</p>
                <p className="mt-2 text-sm text-slate-300">{commodity.note}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr,1fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-xl">Sector impact map</CardTitle>
            <CardDescription>
              First-order impact plus the second-order channel that tends to matter once the market moves beyond headlines.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="h-[380px]">
              {chartsReady ? (
                <ResponsiveContainer width="100%" height="100%" minWidth={280} minHeight={360}>
                  <BarChart data={sectorRows} layout="vertical" margin={{ top: 0, right: 20, left: 30, bottom: 0 }}>
                    <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis type="number" domain={[-5, 5]} tickLine={false} axisLine={false} />
                    <YAxis type="category" dataKey="sector" width={130} tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
                    <Tooltip
                      cursor={{ fill: "rgba(148, 163, 184, 0.12)" }}
                      formatter={(value) => [Number(value ?? 0).toFixed(2), "Impact score"]}
                      contentStyle={{ borderRadius: 14, borderColor: "#e2e8f0" }}
                    />
                    <Bar dataKey="score" radius={[6, 6, 6, 6]}>
                      {sectorRows.map((row) => (
                        <Cell key={row.sector} fill={fillColor(row.score)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full rounded-2xl border border-dashed border-slate-200 bg-slate-50" />
              )}
            </div>
            <div className="grid gap-3">
              {sectorRows.slice(0, 4).concat(sectorRows.slice(-2)).map((sector) => (
                <div key={`${sector.sector}-detail`} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="font-semibold">{sector.sector}</p>
                    <span className={cn("text-sm font-semibold", scoreClass(sector.score))}>
                      {formatSigned(sector.score, " score")}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-700">{sector.firstOrder}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{sector.secondOrder}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-xl">India market cross-currents</CardTitle>
            <CardDescription>
              Index-level bias is dominated by imported energy exposure, rate repricing, and the mix between energy, defence, banks, and consumption inside India.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {regionalRows.map((region) => (
              <div key={region.name} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold">{region.name}</p>
                    <p className="text-sm text-muted-foreground">{region.note}</p>
                  </div>
                  <div className="text-right">
                    <p className={cn("text-lg font-semibold", scoreClass(region.move))}>{formatSigned(region.move)}</p>
                    <p className="text-sm text-muted-foreground">{region.regime}</p>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-xl">Representative India equity map</CardTitle>
          <CardDescription>
            Modeled 2-6 week move ranges for representative NSE names. Live spot prices are shown where the backend feed has them.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[1040px] text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-3 font-medium">Ticker</th>
                <th className="pb-3 font-medium">Company</th>
                <th className="pb-3 font-medium">Region</th>
                <th className="pb-3 font-medium">Sector</th>
                <th className="pb-3 font-medium text-right">Live</th>
                <th className="pb-3 font-medium text-right">1D</th>
                <th className="pb-3 font-medium text-right">Scenario move</th>
                <th className="pb-3 font-medium text-right">Center</th>
                <th className="pb-3 font-medium">Why it matters</th>
              </tr>
            </thead>
            <tbody>
              {equityRows.map((equity) => (
                <tr key={equity.ticker} className="border-b last:border-b-0">
                  <td className="py-3 font-semibold">{equity.ticker}</td>
                  <td className="py-3">{equity.name}</td>
                  <td className="py-3">{equity.region}</td>
                  <td className="py-3">{equity.sector}</td>
                  <td className="py-3 text-right">{equity.liveQuote ? formatLiveValue(equity.liveQuote) : "..."}</td>
                  <td className={cn("py-3 text-right", changeTone(equity.liveQuote?.change_percent))}>
                    {formatLiveChange(equity.liveQuote?.change_percent)}
                  </td>
                  <td className={cn("py-3 text-right font-semibold", scoreClass(equity.center))}>
                    {`${formatSigned(equity.min)} to ${formatSigned(equity.max)}`}
                  </td>
                  <td className={cn("py-3 text-right", scoreClass(equity.center))}>{formatSigned(equity.center)}</td>
                  <td className="py-3 text-muted-foreground">{equity.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-xl">India + global risk confirmation board</CardTitle>
            <CardDescription>
              These cross-asset indicators help you decide whether the oil shock is staying sector-specific or becoming a wider macro regime shift for Indian equities.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {indicators.map((indicator) => (
              <div key={indicator.name} className="grid gap-3 rounded-2xl border border-slate-200 p-4 md:grid-cols-[1.2fr,0.8fr,1.6fr] md:items-center">
                <div>
                  <p className="font-semibold">{indicator.name}</p>
                  <p className="text-sm text-muted-foreground">{indicator.ticker}</p>
                </div>
                <div>
                  <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1", indicatorTone(indicator.level, indicator.caution, indicator.stress))}>
                    {indicator.state}
                  </span>
                  <p className="mt-2 text-lg font-semibold">
                    {indicator.unit === "%" ? `${indicator.level.toFixed(2)}${indicator.unit}` : indicator.unit === "$k" ? `$${indicator.level.toFixed(1)}${indicator.unit}` : indicator.unit === "$" ? `$${indicator.level.toFixed(1)}` : `${indicator.level.toFixed(1)}${indicator.unit}`}
                  </p>
                </div>
                <div className="text-sm text-muted-foreground">
                  <p>{indicator.note}</p>
                  <p className="mt-1">
                    Caution at {indicator.caution}
                    {indicator.unit} and stress at {indicator.stress}
                    {indicator.unit}.
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-[linear-gradient(180deg,_rgba(255,247,237,0.9),_rgba(255,255,255,1))]">
          <CardHeader>
            <CardTitle className="text-xl">Hormuz disruption transmission</CardTitle>
            <CardDescription>
              A visual flow of how physical disruption rolls into commodities, Indian margins, inflation, and earnings.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-3 lg:grid-cols-2">
              {FLOW_STEPS.map((step, index) => {
                const Icon = step.icon;
                const value = transmission[step.key as keyof typeof transmission];
                return (
                  <div key={step.key} className="relative rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Step {index + 1}</p>
                        <h3 className="mt-1 font-semibold">{step.title}</h3>
                      </div>
                      <div className="rounded-xl bg-slate-900 p-2 text-white">
                        <Icon className="h-4 w-4" />
                      </div>
                    </div>
                    <div className="mt-4 h-2 rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-orange-500 to-rose-500"
                        style={{ width: `${value}%` }}
                      />
                    </div>
                    <p className="mt-3 text-sm font-semibold text-slate-900">{value.toFixed(0)}/100 intensity</p>
                    {index < FLOW_STEPS.length - 1 && (
                      <ArrowRight className="absolute -bottom-3 right-6 hidden h-5 w-5 rounded-full bg-white text-slate-400 lg:block" />
                    )}
                  </div>
                );
              })}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <MiniStat title="Tanker and insurance stress" value={`${transmission.freight.toFixed(0)}/100`} note="Shipping friction is the earliest confirmation signal." />
              <MiniStat title="Airline margin hit" value={`${transmission.airline.toFixed(0)}/100`} note="Watch relative underperformance in airlines and travel." />
              <MiniStat title="Energy revenue uplift" value={`${transmission.energy.toFixed(0)}/100`} note="Large integrated oils convert price shocks into earnings fast." />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr,1fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-xl">Operating playbook</CardTitle>
            <CardDescription>
              Use these buckets to turn a noisy news cycle into a repeatable process.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {signalStack.map((stack) => (
              <div key={stack.title} className="rounded-2xl border border-slate-200 p-4">
                <p className="font-semibold">{stack.title}</p>
                <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                  {stack.items.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-slate-950 text-white">
          <CardHeader>
            <CardTitle className="text-xl">What to read from the dashboard</CardTitle>
            <CardDescription className="text-slate-400">
              This model is most useful when the indicators line up across commodities, rates, INR, and India equity leadership.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-slate-300">
            <InsightRow
              icon={TrendingUp}
              title="First-order winners"
              text="ONGC, Oil India, Reliance, and defence PSUs should lead if the shock stays concentrated in energy and security."
            />
            <InsightRow
              icon={TrendingDown}
              title="First-order losers"
              text="IndiGo, OMCs, paints, chemical names, and domestic consumption typically lag once oil, INR, and rates all tighten together."
            />
            <InsightRow
              icon={Fuel}
              title="Second-order shift"
              text="If Brent, USD/INR, India VIX, and bank underperformance all worsen together, the market stops treating this as a temporary commodity event and starts pricing a broader India slowdown."
            />
            <InsightRow
              icon={ShieldAlert}
              title="Key discipline"
              text="Do not overreact to single headlines. Use physical-market confirmation like tanker disruption, freight stress, Brent persistence, and INR weakness before leaning too far into the tail scenario."
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function HeroStat({
  label,
  value,
  note,
  compact = false,
}: {
  label: string;
  value: string;
  note: string;
  compact?: boolean;
}) {
  return (
    <div className={cn("rounded-2xl border border-white/10 bg-white/5 p-4", compact && "sm:col-span-2")}>
      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <p className="mt-2 text-lg font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm text-slate-300">{note}</p>
    </div>
  );
}

function ControlRow({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-4">
        <p className="font-medium">{label}</p>
        <span className="text-sm text-muted-foreground">{value}</span>
      </div>
      {children}
    </div>
  );
}

function MiniStat({
  title,
  value,
  note,
}: {
  title: string;
  value: string;
  note: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{title}</p>
      <p className="mt-2 text-lg font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-muted-foreground">{note}</p>
    </div>
  );
}

function MetricCard({
  title,
  value,
  footnote,
  tone,
}: {
  title: string;
  value: string;
  footnote: string;
  tone: string;
}) {
  return (
    <Card className={cn("border-slate-200 bg-gradient-to-br", tone)}>
      <CardContent className="pt-6">
        <p className="text-sm text-slate-600">{title}</p>
        <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
        <p className="mt-2 text-sm text-slate-600">{footnote}</p>
      </CardContent>
    </Card>
  );
}

function InsightRow({
  icon: Icon,
  title,
  text,
}: {
  icon: typeof TrendingUp;
  title: string;
  text: string;
}) {
  return (
    <div className="flex gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="rounded-xl bg-white/10 p-2">
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <p className="font-semibold text-white">{title}</p>
        <p className="mt-1 text-sm text-slate-300">{text}</p>
      </div>
    </div>
  );
}
