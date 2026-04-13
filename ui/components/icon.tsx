interface IconProps {
  name: string;
  className?: string;
  size?: number;
}

export function Icon({ name, className = "", size = 24 }: IconProps) {
  return (
    <span
      className={`material-symbols-outlined inline-flex items-center justify-center leading-none ${className}`}
      style={{ fontSize: size, width: size, height: size }}
    >
      {name}
    </span>
  );
}
