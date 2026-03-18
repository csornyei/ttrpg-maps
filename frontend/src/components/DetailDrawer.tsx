import type { PoiDetail } from "../types";

interface DetailDrawerProps {
  detail: PoiDetail | null;
  isOpen: boolean;
  onClose: () => void;
}

export function DetailDrawer({ detail, isOpen, onClose }: DetailDrawerProps) {
  if (!detail) return null;

  return (
    <div className={`drawer ${isOpen ? "drawer--open" : ""}`}>
      <div className="drawer__header">
        <h2 className="drawer__title" style={{ color: detail.color }}>
          {detail.name}
        </h2>
        <button className="drawer__close" onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="drawer__body">
        <p className="drawer__description">{detail.description}</p>
      </div>
    </div>
  );
}
