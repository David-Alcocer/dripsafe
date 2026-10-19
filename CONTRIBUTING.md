# Cómo trabajamos con Git

## Metodología: trunk-based development

- `main` es la única rama permanente y **siempre debe funcionar**.
- Cada tarea va en una **rama corta** que vive horas, no días.
- Se integra a `main` con un **PR pequeño** y una revisión rápida de otra persona.
- Nada de ramas `develop` ni `release`: en 3 días solo generan conflictos.

### Nombres de rama

```text
feat/modelo-isolation-forest
feat/dashboard-alertas
data/limpieza-kit
docs/analisis-acuifero
fix/calculo-pue
```

### Flujo

```bash
git switch main && git pull
git switch -c feat/mi-tarea
# ... trabajar, commits pequeños ...
git push -u origin feat/mi-tarea
# abrir PR → alguien revisa → merge a main → borrar la rama
```

### Commits

Mensajes cortos, en presente y en español:

```text
feat: agrega cálculo de PUE por hora
fix: corrige columnas nulas en kit
docs: agrega fuentes del acuífero
```

## git worktree (opcional)

Permite tener **varias ramas abiertas a la vez en carpetas separadas** del mismo repo, sin `stash` ni cambiar de rama. Recomendado para quien trabaja con Claude o la terminal (Misa y Guille). No es obligatorio.

```bash
# Abrir la rama de un PR en otra carpeta para probarla
git worktree add ../dripsafe-revision feat/dashboard-alertas

# Tener siempre a mano una copia estable de main (útil el día 22)
git worktree add ../dripsafe-estable main

# Ver y limpiar
git worktree list
git worktree remove ../dripsafe-revision
```

## Reglas

- 🚫 **Nunca subir `data/`.** El kit de datos es confidencial y ya está en `.gitignore`.
- 🚫 Nada de llaves, contraseñas ni archivos `.env` en el repo.
- ✅ Antes de hacer merge, `main` debe seguir corriendo (notebook o `streamlit run app/main.py`).
- ✅ El miércoles 21 en la noche se congela `main`: el 22 solo entran arreglos.
