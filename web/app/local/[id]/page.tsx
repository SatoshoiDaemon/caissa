import { GamePage } from "../../../components/game-page";

export default async function LocalPage({ params }: { params: Promise<{id: string}> }) {
  const { id } = await params;
  return <GamePage key={id} id={id} local />;
}
