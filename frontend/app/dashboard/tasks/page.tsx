import TaskRequestForm from '../../../components/Dashboard/TaskRequestForm';
import TaskQueue from '../../../components/Dashboard/TaskQueue';

export default function TasksPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">AI Tasks</h1>
      <TaskRequestForm />
      <TaskQueue />
    </div>
  );
}
