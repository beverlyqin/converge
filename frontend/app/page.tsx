"use client";

import { useState, type FormEvent } from "react";

type FlightSegment = {
  flight_number: string;
  operating_carrier: string;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
};

type Itinerary = {
  segments: FlightSegment[];
};

type MeetupSearchResult = {
  destination: string;
  score: number;
  backup_options: number;
  itinerary_a: Itinerary;
  itinerary_b: Itinerary;
  metrics: {
    arrival_gap_minutes: number;
    total_stops: number;
    total_travel_time_minutes: number;
  };
  component_scores: {
    arrival_sync: number;
    stops: number;
    travel_time: number;
  };
  explanation: {
    reasons: string[];
  };
};

function formatDateTime(value: string) {
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function ItineraryCard({
  label,
  itinerary,
}: {
  label: string;
  itinerary: Itinerary;
}) {
  const first = itinerary.segments[0];
  const last = itinerary.segments[itinerary.segments.length - 1];

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xl font-semibold">{first.origin}</p>
          <p className="text-sm text-slate-500">
            {formatDateTime(first.departure_time)}
          </p>
        </div>

        <div className="flex-1 text-center">
          <p className="text-xs text-slate-400">
            {itinerary.segments.length === 1
              ? "Nonstop"
              : `${itinerary.segments.length - 1} stop`}
          </p>

          <div className="my-2 h-px bg-slate-300" />

          <p className="text-xs font-medium text-slate-500">
            {itinerary.segments.map((segment) => segment.flight_number).join(" · ")}
          </p>
        </div>

        <div className="text-right">
          <p className="text-xl font-semibold">{last.destination}</p>
          <p className="text-sm text-slate-500">
            {formatDateTime(last.arrival_time)}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [originA, setOriginA] = useState("JFK");
  const [originB, setOriginB] = useState("SEA");

  const [departAfterA, setDepartAfterA] =
    useState("2026-11-13T17:00");

  const [departBeforeA, setDepartBeforeA] =
    useState("2026-11-13T23:59");

  const [departAfterB, setDepartAfterB] =
    useState("2026-11-13T14:00");

  const [departBeforeB, setDepartBeforeB] =
    useState("2026-11-13T20:00");

  const [roundTrip, setRoundTrip] = useState(false);

  const [returnAfterA, setReturnAfterA] =
    useState("2026-11-15T15:00");
  
  const [returnBeforeA, setReturnBeforeA] =
    useState("2026-11-15T20:00");
  
  const [returnAfterB, setReturnAfterB] =
    useState("2026-11-15T15:00");
  
  const [returnBeforeB, setReturnBeforeB] =
    useState("2026-11-15T20:00");

  const [maxStops, setMaxStops] = useState(1);
  const [maxArrivalGap, setMaxArrivalGap] = useState(120);
  const [arrivalWeight, setArrivalWeight] = useState(4);
  const [stopsWeight, setStopsWeight] = useState(2);
  const [travelTimeWeight, setTravelTimeWeight] = useState(3);
  const [backupWeight, setBackupWeight] = useState(1);

  const [results, setResults] = useState<MeetupSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    
    setLoading(true);
    setError("");
    setResults([]);

    const totalWeight =
    arrivalWeight +
    stopsWeight +
    travelTimeWeight +
    backupWeight;

    if (totalWeight === 0) {
      setError("Choose at least one ranking preference.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("/api/meetups", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          traveler_a: {
            origin: originA.toUpperCase(),
            depart_after: departAfterA,
            depart_before: departBeforeA,
            ...(roundTrip && {
              return_after: returnAfterA,
              return_before: returnBeforeA,
            }),
          },
          traveler_b: {
            origin: originB.toUpperCase(),
            depart_after: departAfterB,
            depart_before: departBeforeB,
            ...(roundTrip && {
              return_after: returnAfterB,
              return_before: returnBeforeB,
            }),
          },
          constraints: {
            max_stops: maxStops,
            max_arrival_gap_minutes: maxArrivalGap,
          },
          weights: {
            arrival_sync: arrivalWeight / totalWeight,
            stops: stopsWeight / totalWeight,
            travel_time: travelTimeWeight / totalWeight,
            backup_options: backupWeight / totalWeight,
          },
        }),
      });

      if (!response.ok) {
        throw new Error("Search failed. Check that the backend is running.");
      }

      const data: MeetupSearchResult[] = await response.json();
      setResults(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <header className="mb-10">
          <div className="mb-4 inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm">
            Group flight planning
          </div>

          <h1 className="max-w-3xl text-5xl font-semibold tracking-tight">
            Meet somewhere that works for everyone.
          </h1>

          <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-500">
            Compare flight options from different cities and find meeting
            destinations that balance arrival time, travel time, stops, and
            backup options.
          </p>
        </header>

        <div className="grid gap-8 lg:grid-cols-[390px_1fr]">
          <form
            onSubmit={handleSubmit}
            className="h-fit rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <h2 className="text-lg font-semibold">Plan a meetup</h2>
            <p className="mt-1 text-sm text-slate-500">
              Enter each traveler&apos;s departure window.
            </p>

            <div className="mt-7 space-y-7">
              <div className="flex rounded-xl bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => setRoundTrip(false)}
                  className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${
                    !roundTrip
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500"
                  }`}
                >
                  One way
                </button>

                <button
                  type="button"
                  onClick={() => setRoundTrip(true)}
                  className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${
                    roundTrip
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500"
                  }`}
                >
                  Round trip
                </button>
              </div>
              <section>
                <p className="mb-3 text-sm font-semibold">Traveler A</p>

                <div className="space-y-3">
                  <input
                    value={originA}
                    onChange={(e) => setOriginA(e.target.value)}
                    placeholder="Origin airport"
                    maxLength={3}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 uppercase outline-none transition focus:border-slate-400"
                  />

                  <label className="block text-xs font-medium text-slate-500">
                    Earliest departure
                  </label>

                  <input
                    type="datetime-local"
                    value={departAfterA}
                    onChange={(e) => setDepartAfterA(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                  />

                  <label className="block text-xs font-medium text-slate-500">
                    Latest departure
                  </label>

                  <input
                    type="datetime-local"
                    value={departBeforeA}
                    onChange={(e) => setDepartBeforeA(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                  />

                  {roundTrip && (
                    <>
                      <label className="block text-xs font-medium text-slate-500">
                        Earliest return
                      </label>

                      <input
                        type="datetime-local"
                        value={returnAfterA}
                        onChange={(e) => setReturnAfterA(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                      />

                      <label className="block text-xs font-medium text-slate-500">
                        Latest return
                      </label>

                      <input
                        type="datetime-local"
                        value={returnBeforeA}
                        onChange={(e) => setReturnBeforeA(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                      />
                    </>
                  )}
                </div>
              </section>

              <div className="border-t border-slate-100" />

              <section>
                <p className="mb-3 text-sm font-semibold">Traveler B</p>

                <div className="space-y-3">
                  <input
                    value={originB}
                    onChange={(e) => setOriginB(e.target.value)}
                    placeholder="Origin airport"
                    maxLength={3}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 uppercase outline-none transition focus:border-slate-400"
                  />

                  <label className="block text-xs font-medium text-slate-500">
                    Earliest departure
                  </label>

                  <input
                    type="datetime-local"
                    value={departAfterB}
                    onChange={(e) => setDepartAfterB(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                  />

                  <label className="block text-xs font-medium text-slate-500">
                    Latest departure
                  </label>

                  <input
                    type="datetime-local"
                    value={departBeforeB}
                    onChange={(e) => setDepartBeforeB(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                  />

                  {roundTrip && (
                    <>
                      <label className="block text-xs font-medium text-slate-500">
                        Earliest return
                      </label>

                      <input
                        type="datetime-local"
                        value={returnAfterB}
                        onChange={(e) => setReturnAfterB(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                      />

                      <label className="block text-xs font-medium text-slate-500">
                        Latest return
                      </label>

                      <input
                        type="datetime-local"
                        value={returnBeforeB}
                        onChange={(e) => setReturnBeforeB(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                      />
                    </>
                  )}
                </div>
              </section>

              <p className="text-xs text-slate-400">
                Departure times are interpreted in each origin airport&apos;s local time.
              </p>

              <div className="border-t border-slate-100" />

              <section className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium">
                    Maximum stops
                  </label>

                  <select
                    value={maxStops}
                    onChange={(e) => setMaxStops(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3"
                  >
                    <option value={0}>Nonstop only</option>
                    <option value={1}>Up to 1 stop</option>
                  </select>
                </div>

                <div>
                  <div className="mb-2 flex justify-between text-sm">
                    <label className="font-medium">
                      Maximum arrival gap
                    </label>
                    <span className="text-slate-500">
                      {maxArrivalGap} min
                    </span>
                  </div>
                  <div className="border-t border-slate-100 pt-5">
                    <p className="mb-1 text-sm font-semibold">
                      Ranking preferences
                    </p>

                    <p className="mb-5 text-xs leading-5 text-slate-400">
                      Higher values make that factor more important when ranking
                      feasible destinations.
                    </p>

                    <div className="space-y-4">
                      <div>
                        <div className="mb-2 flex justify-between text-sm">
                          <label>Arrive together</label>
                          <span>{arrivalWeight}</span>
                        </div>

                        <input
                          type="range"
                          min="0"
                          max="10"
                          value={arrivalWeight}
                          onChange={(e) =>
                            setArrivalWeight(Number(e.target.value))
                          }
                          className="w-full"
                        />
                      </div>

                      <div>
                        <div className="mb-2 flex justify-between text-sm">
                          <label>Fewer stops</label>
                          <span>{stopsWeight}</span>
                        </div>

                        <input
                          type="range"
                          min="0"
                          max="10"
                          value={stopsWeight}
                          onChange={(e) =>
                            setStopsWeight(Number(e.target.value))
                          }
                          className="w-full"
                        />
                      </div>

                      <div>
                        <div className="mb-2 flex justify-between text-sm">
                          <label>Shorter travel time</label>
                          <span>{travelTimeWeight}</span>
                        </div>

                        <input
                          type="range"
                          min="0"
                          max="10"
                          value={travelTimeWeight}
                          onChange={(e) =>
                            setTravelTimeWeight(Number(e.target.value))
                          }
                          className="w-full"
                        />
                      </div>

                      <div>
                        <div className="mb-2 flex justify-between text-sm">
                          <label>Backup options</label>
                          <span>{backupWeight}</span>
                        </div>

                        <input
                          type="range"
                          min="0"
                          max="10"
                          value={backupWeight}
                          onChange={(e) =>
                            setBackupWeight(Number(e.target.value))
                          }
                          className="w-full"
                        />
                      </div>
                    </div>
                  </div>

                  <input
                    type="range"
                    min="30"
                    max="240"
                    step="30"
                    value={maxArrivalGap}
                    onChange={(e) =>
                      setMaxArrivalGap(Number(e.target.value))
                    }
                    className="w-full"
                  />
                </div>
              </section>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-7 w-full rounded-xl bg-slate-950 px-4 py-3 font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Searching..." : "Find meetup options"}
            </button>

            <p className="mt-3 text-center text-xs text-slate-400">
              Live search may use your configured flight provider quota.
            </p>
          </form>

          <section>
            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
                {error}
              </div>
            )}

            {!loading && !error && results.length === 0 && (
              <div className="flex min-h-[430px] items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white/50 p-10 text-center">
                <div>
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm">
                    ✈
                  </div>

                  <h2 className="text-lg font-semibold">
                    Your meetup options will appear here
                  </h2>

                  <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
                    We&apos;ll compare reachable destinations and rank them by
                    group convenience.
                  </p>
                </div>
              </div>
            )}

            {loading && (
              <div className="flex min-h-[430px] items-center justify-center rounded-3xl border border-slate-200 bg-white">
                <p className="text-sm text-slate-500">
                  Comparing flight options...
                </p>
              </div>
            )}

            {results.length > 0 && (
              <div>
                <div className="mb-5 flex items-end justify-between">
                  <div>
                    <p className="text-sm text-slate-500">
                      Ranked meetup options
                    </p>
                    <h2 className="text-2xl font-semibold">
                      Best destinations
                    </h2>
                  </div>

                  <p className="text-sm text-slate-400">
                    {results.length} result
                    {results.length !== 1 && "s"}
                  </p>
                </div>

                <div className="space-y-5">
                  {results.map((result, index) => (
                    <article
                      key={`${result.destination}-${index}`}
                      className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
                    >
                      <div className="mb-6 flex items-start justify-between">
                        <div>
                          <div className="mb-2 flex items-center gap-2">
                            {index === 0 && (
                              <span className="rounded-full bg-slate-950 px-2.5 py-1 text-xs font-medium text-white">
                                Best match
                              </span>
                            )}

                            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                              #{index + 1}
                            </span>
                          </div>

                          <h3 className="text-3xl font-semibold">
                            {result.destination}
                          </h3>
                        </div>

                        <div className="text-right">
                          <p className="text-xs uppercase tracking-wider text-slate-400">
                            Score
                          </p>
                          <p className="text-2xl font-semibold">
                            {result.score.toFixed(2)}
                          </p>
                        </div>
                      </div>

                      <div className="grid gap-3">
                        <ItineraryCard
                          label="Traveler A"
                          itinerary={result.itinerary_a}
                        />

                        <ItineraryCard
                          label="Traveler B"
                          itinerary={result.itinerary_b}
                        />
                      </div>

                      <div className="mt-5 grid grid-cols-3 gap-3">
                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-xs text-slate-400">
                            Arrival gap
                          </p>
                          <p className="mt-1 font-semibold">
                            {Math.round(
                              result.metrics.arrival_gap_minutes
                            )}{" "}
                            min
                          </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-xs text-slate-400">
                            Total stops
                          </p>
                          <p className="mt-1 font-semibold">
                            {result.metrics.total_stops}
                          </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-xs text-slate-400">
                            Backup layers
                          </p>
                          <p className="mt-1 font-semibold">
                            {result.backup_options}
                          </p>
                        </div>
                      </div>

                      <div className="mt-5 border-t border-slate-100 pt-5">
                        <p className="mb-3 text-sm font-semibold">
                          Why this works
                        </p>

                        <ul className="space-y-2 text-sm leading-6 text-slate-600">
                          {result.explanation.reasons.map(
                            (reason, reasonIndex) => (
                              <li
                                key={reasonIndex}
                                className="flex gap-2"
                              >
                                <span className="text-slate-300">•</span>
                                <span>{reason}</span>
                              </li>
                            )
                          )}
                        </ul>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}