import React from 'react';

interface LeaderboardItem {
  rank: number;
  user_id: string;
  points: number;
}

interface Props {
  items: LeaderboardItem[];
}

export default function LeaderboardTable({ items }: Props) {
  if (!items || items.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8' }}>
        No players on the leaderboard yet.
      </div>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>User ID</th>
          <th>Points</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={`${item.user_id}-${item.rank}`}>
            <td className="rank">#{item.rank}</td>
            <td>{item.user_id}</td>
            <td>{item.points.toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}