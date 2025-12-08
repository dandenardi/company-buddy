"use client";

import { useState } from "react";
import useSWR from "swr";

interface OverviewMetrics {
  total_queries: number;
  total_feedbacks: number;
  satisfaction_rate: number;
  avg_response_time_ms: number;
  total_documents: number;
  total_chunks: number;
}

interface QueryMetric {
  date: string;
  count: number;
}

interface CommonQuestion {
  question: string;
  count: number;
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);

  // Fetch data
  const { data: overview, isLoading: overviewLoading } =
    useSWR<OverviewMetrics>(`/api/v1/analytics/overview?days=${days}`);

  const { data: queries, isLoading: queriesLoading } = useSWR<QueryMetric[]>(
    `/api/v1/analytics/queries?days=${days}`,
  );

  const { data: commonQuestions, isLoading: questionsLoading } = useSWR<
    CommonQuestion[]
  >(`/api/v1/analytics/common-questions?days=${days}&limit=10`);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
            <p className="text-gray-600 mt-1">
              Monitor your RAG system performance
            </p>
          </div>

          {/* Date Range Selector */}
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg bg-white shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>

        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Queries"
            value={overview?.total_queries || 0}
            icon="📊"
            loading={overviewLoading}
          />
          <MetricCard
            title="Satisfaction Rate"
            value={`${overview?.satisfaction_rate || 0}%`}
            icon="😊"
            color={
              overview && overview.satisfaction_rate > 80
                ? "green"
                : overview && overview.satisfaction_rate > 50
                  ? "yellow"
                  : "red"
            }
            loading={overviewLoading}
          />
          <MetricCard
            title="Avg Response Time"
            value={`${overview?.avg_response_time_ms || 0}ms`}
            icon="⚡"
            loading={overviewLoading}
          />
          <MetricCard
            title="Total Documents"
            value={overview?.total_documents || 0}
            icon="📄"
            loading={overviewLoading}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Queries Over Time */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">
              Queries Over Time
            </h2>
            {queriesLoading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="text-gray-400">Loading...</div>
              </div>
            ) : queries && queries.length > 0 ? (
              <SimpleBarChart data={queries} />
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-gray-500">No data available</p>
              </div>
            )}
          </div>

          {/* Common Questions */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">
              Most Common Questions
            </h2>
            {questionsLoading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="text-gray-400">Loading...</div>
              </div>
            ) : commonQuestions && commonQuestions.length > 0 ? (
              <ul className="space-y-3">
                {commonQuestions.map((q, idx) => (
                  <li
                    key={idx}
                    className="flex justify-between items-start gap-4 p-3 hover:bg-gray-50 rounded-lg transition-colors"
                  >
                    <span className="text-sm text-gray-700 flex-1 line-clamp-2">
                      {q.question}
                    </span>
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-xs font-medium whitespace-nowrap">
                      {q.count}x
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="h-64 flex items-center justify-center">
                <p className="text-gray-500">No questions yet</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper Components
interface MetricCardProps {
  title: string;
  value: string | number;
  icon: string;
  color?: "blue" | "green" | "yellow" | "red";
  loading?: boolean;
}

function MetricCard({
  title,
  value,
  icon,
  color = "blue",
  loading,
}: MetricCardProps) {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    yellow: "bg-yellow-50 text-yellow-700",
    red: "bg-red-50 text-red-700",
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        <span className="text-2xl">{icon}</span>
      </div>
      {loading ? (
        <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
      ) : (
        <p className={`text-3xl font-bold ${colorClasses[color]}`}>{value}</p>
      )}
    </div>
  );
}

function SimpleBarChart({ data }: { data: QueryMetric[] }) {
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  // Show last 14 days
  const recentData = data.slice(-14);

  return (
    <div className="space-y-2">
      {recentData.map((item, idx) => {
        const percentage = (item.count / maxCount) * 100;

        return (
          <div key={idx} className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-20 text-right font-medium">
              {new Date(item.date).toLocaleDateString("pt-BR", {
                month: "short",
                day: "numeric",
              })}
            </span>
            <div className="flex-1 bg-gray-100 rounded-full h-8 relative overflow-hidden">
              <div
                className="bg-gradient-to-r from-indigo-500 to-indigo-600 h-8 rounded-full flex items-center justify-end pr-3 transition-all duration-300"
                style={{ width: `${Math.max(percentage, 5)}%` }}
              >
                {item.count > 0 && (
                  <span className="text-xs text-white font-semibold">
                    {item.count}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
      {recentData.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          No query data available
        </div>
      )}
    </div>
  );
}
