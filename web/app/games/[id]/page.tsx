import { Replay } from "../../../components/replay";

export default async function ReplayPage({ params }: { params: Promise<{id: string}> }) {
  const { id } = await params;
  return <Replay key={id} id={id} />;
}
