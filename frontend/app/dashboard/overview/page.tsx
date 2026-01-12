import OverviewCards from '../../../components/Dashboard/OverviewCards';

export default function OverviewPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">System Overview</h1>
      <OverviewCards />
      {/* Add charts, real-time stats, insights here */}
    </div>
  );
}

