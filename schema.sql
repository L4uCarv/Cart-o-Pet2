-- Extensão para UUIDs
create extension if not exists "uuid-ossp";

-- 1. Perfis de Utilizador Multi-nível
create table public.perfis (
    id uuid references auth.users on delete cascade primary key,
    nome text not null,
    email text unique not null,
    papel text check (papel in ('tutor', 'criador', 'clinica', 'admin')) default 'tutor',
    criado_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. Animais de Estimação
create table public.animais (
    id uuid default uuid_generate_v4() primary key,
    tutor_id uuid references public.perfis(id) on delete cascade not null,
    nome text not null,
    especie text not null, -- ex: Cão, Gato
    raca text,
    idade_anos int,
    peso numeric(5,2),
    foto_url text,
    criado_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. Registos de Vacinas e Desparasitação
create table public.registos_medicos (
    id uuid default uuid_generate_v4() primary key,
    animal_id uuid references public.animais(id) on delete cascade not null,
    tipo text check (tipo in ('vacina', 'desparasitacao')) not null,
    nome_produto text not null, -- ex: Raiva, Nobivac, Drontal
    data_aplicacao date not null,
    proxima_dose date not null,
    admin_por uuid references public.perfis(id),
    observacoes text,
    criado_at timestamp with time zone default timezone('utc'::text, now()) not null