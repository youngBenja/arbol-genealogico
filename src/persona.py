class Persona:
    def __init__(
        self,
        id_persona: str,
        nombre: str,
        parentesco: str = "",
        fecha_nacimiento: str | None = None,
        fecha_fallecimiento: str | None = None,
        descripcion: str = "",
        foto: str | None = None,
        fuentes: list[str] | None = None,
    ):
        self.id = id_persona
        self.nombre = nombre
        self.parentesco = parentesco
        self.fecha_nacimiento = fecha_nacimiento
        self.fecha_fallecimiento = fecha_fallecimiento
        self.descripcion = descripcion
        self.foto = foto
        self.fuentes = fuentes if fuentes is not None else []

        self.padres: list["Persona"] = []
        self.hijos: list["Persona"] = []
        self.conyuge: "Persona | None" = None

    def agregar_hijo(self, hijo: "Persona") -> None:
        """Registra a un hijo y conecta bidireccionalmente padre <-> hijo."""
        if hijo not in self.hijos:
            self.hijos.append(hijo)
        if self not in hijo.padres:
            hijo.padres.append(self)

    def asignar_conyuge(self, pareja: "Persona") -> None:
        """Asigna el cónyuge de forma mutua evitando autorreferencia."""
        if pareja is self:
            return
        self.conyuge = pareja
        pareja.conyuge = self

    def obtener_hermanos(self, incluir_medios: bool = True) -> list["Persona"]:
        """Devuelve hermanos completos o medios hermanos según los padres registrados."""
        if not self.padres:
            return []

        candidatos: dict[str, "Persona"] = {}
        for padre in self.padres:
            for hijo in padre.hijos:
                if hijo.id == self.id:
                    continue
                if incluir_medios:
                    candidatos[hijo.id] = hijo
                else:
                    mismos_padres = {p.id for p in hijo.padres} == {p.id for p in self.padres}
                    if mismos_padres:
                        candidatos[hijo.id] = hijo

        return list(candidatos.values())

    def __repr__(self) -> str:
        return (
            f"Persona(id={self.id!r}, nombre={self.nombre!r}, "
            f"parentesco={self.parentesco!r})"
        )