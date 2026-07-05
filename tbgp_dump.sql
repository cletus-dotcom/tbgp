--
-- PostgreSQL database dump
--

\restrict 2Evxpig4Zmz10ktRzr0m0lKKUziQGwxTT4yughFZkRYlQhevxFdSU1ivNetfqK1

-- Dumped from database version 15.18
-- Dumped by pg_dump version 15.18

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_member_id_fkey;
ALTER TABLE IF EXISTS ONLY public.sharing_entries DROP CONSTRAINT IF EXISTS sharing_entries_project_id_fkey;
ALTER TABLE IF EXISTS ONLY public.sharing_entries DROP CONSTRAINT IF EXISTS sharing_entries_member_id_fkey;
ALTER TABLE IF EXISTS ONLY public.sharing_entries DROP CONSTRAINT IF EXISTS sharing_entries_billing_id_fkey;
ALTER TABLE IF EXISTS ONLY public.sharing_entries DROP CONSTRAINT IF EXISTS sharing_entries_batch_id_fkey;
ALTER TABLE IF EXISTS ONLY public.project_commissions DROP CONSTRAINT IF EXISTS project_commissions_contractor_referrer_id_fkey;
ALTER TABLE IF EXISTS ONLY public.project_commissions DROP CONSTRAINT IF EXISTS project_commissions_contractor_id_fkey;
ALTER TABLE IF EXISTS ONLY public.project_commissions DROP CONSTRAINT IF EXISTS project_commissions_client_referrer_id_fkey;
ALTER TABLE IF EXISTS ONLY public.project_billings DROP CONSTRAINT IF EXISTS project_billings_project_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payout_requests DROP CONSTRAINT IF EXISTS payout_requests_requested_by_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payout_requests DROP CONSTRAINT IF EXISTS payout_requests_request_reviewed_by_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payout_requests DROP CONSTRAINT IF EXISTS payout_requests_release_submitted_by_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payout_requests DROP CONSTRAINT IF EXISTS payout_requests_release_approved_by_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payout_requests DROP CONSTRAINT IF EXISTS payout_requests_rejected_by_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payout_requests DROP CONSTRAINT IF EXISTS payout_requests_member_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payout_notifications DROP CONSTRAINT IF EXISTS payout_notifications_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.payout_notifications DROP CONSTRAINT IF EXISTS payout_notifications_payout_id_fkey;
ALTER TABLE IF EXISTS ONLY public.ompd_fund_entries DROP CONSTRAINT IF EXISTS ompd_fund_entries_payout_id_fkey;
ALTER TABLE IF EXISTS ONLY public.ompd_fund_entries DROP CONSTRAINT IF EXISTS ompd_fund_entries_member_id_fkey;
ALTER TABLE IF EXISTS ONLY public.members DROP CONSTRAINT IF EXISTS members_referrer_id_fkey;
ALTER TABLE IF EXISTS ONLY public.member_ledger DROP CONSTRAINT IF EXISTS member_ledger_project_id_fkey;
ALTER TABLE IF EXISTS ONLY public.member_ledger DROP CONSTRAINT IF EXISTS member_ledger_payout_request_id_fkey;
ALTER TABLE IF EXISTS ONLY public.member_ledger DROP CONSTRAINT IF EXISTS member_ledger_member_id_fkey;
ALTER TABLE IF EXISTS ONLY public.member_ledger DROP CONSTRAINT IF EXISTS member_ledger_entry_id_fkey;
ALTER TABLE IF EXISTS ONLY public.member_ledger DROP CONSTRAINT IF EXISTS member_ledger_billing_id_fkey;
ALTER TABLE IF EXISTS ONLY public.member_ledger DROP CONSTRAINT IF EXISTS member_ledger_batch_id_fkey;
ALTER TABLE IF EXISTS ONLY public.contractors DROP CONSTRAINT IF EXISTS contractors_member_referrer_id_fkey;
DROP INDEX IF EXISTS public.uq_commission_levels_scheme_level;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_username_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.sharing_entries DROP CONSTRAINT IF EXISTS sharing_entries_pkey;
ALTER TABLE IF EXISTS ONLY public.sharing_batches DROP CONSTRAINT IF EXISTS sharing_batches_pkey;
ALTER TABLE IF EXISTS ONLY public.project_commissions DROP CONSTRAINT IF EXISTS project_commissions_pkey;
ALTER TABLE IF EXISTS ONLY public.project_billings DROP CONSTRAINT IF EXISTS project_billings_pkey;
ALTER TABLE IF EXISTS ONLY public.payout_requests DROP CONSTRAINT IF EXISTS payout_requests_pkey;
ALTER TABLE IF EXISTS ONLY public.payout_notifications DROP CONSTRAINT IF EXISTS payout_notifications_pkey;
ALTER TABLE IF EXISTS ONLY public.ompd_fund_entries DROP CONSTRAINT IF EXISTS ompd_fund_entries_pkey;
ALTER TABLE IF EXISTS ONLY public.ompd_fund_entries DROP CONSTRAINT IF EXISTS ompd_fund_entries_payout_id_key;
ALTER TABLE IF EXISTS ONLY public.members DROP CONSTRAINT IF EXISTS members_pkey;
ALTER TABLE IF EXISTS ONLY public.member_ledger DROP CONSTRAINT IF EXISTS member_ledger_pkey;
ALTER TABLE IF EXISTS ONLY public.contractors DROP CONSTRAINT IF EXISTS contractors_pkey;
ALTER TABLE IF EXISTS ONLY public.commission_levels DROP CONSTRAINT IF EXISTS commission_levels_pkey;
ALTER TABLE IF EXISTS public.users ALTER COLUMN user_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.sharing_entries ALTER COLUMN entry_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.sharing_batches ALTER COLUMN batch_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.project_commissions ALTER COLUMN project_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.project_billings ALTER COLUMN billing_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.payout_requests ALTER COLUMN payout_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.payout_notifications ALTER COLUMN notification_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.ompd_fund_entries ALTER COLUMN entry_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.members ALTER COLUMN member_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.member_ledger ALTER COLUMN ledger_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.contractors ALTER COLUMN contractor_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.commission_levels ALTER COLUMN level_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.users_user_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.sharing_entries_entry_id_seq;
DROP TABLE IF EXISTS public.sharing_entries;
DROP SEQUENCE IF EXISTS public.sharing_batches_batch_id_seq;
DROP TABLE IF EXISTS public.sharing_batches;
DROP SEQUENCE IF EXISTS public.project_commissions_project_id_seq;
DROP TABLE IF EXISTS public.project_commissions;
DROP SEQUENCE IF EXISTS public.project_billings_billing_id_seq;
DROP TABLE IF EXISTS public.project_billings;
DROP SEQUENCE IF EXISTS public.payout_requests_payout_id_seq;
DROP TABLE IF EXISTS public.payout_requests;
DROP SEQUENCE IF EXISTS public.payout_notifications_notification_id_seq;
DROP TABLE IF EXISTS public.payout_notifications;
DROP SEQUENCE IF EXISTS public.ompd_fund_entries_entry_id_seq;
DROP TABLE IF EXISTS public.ompd_fund_entries;
DROP SEQUENCE IF EXISTS public.members_member_id_seq;
DROP TABLE IF EXISTS public.members;
DROP SEQUENCE IF EXISTS public.member_ledger_ledger_id_seq;
DROP TABLE IF EXISTS public.member_ledger;
DROP SEQUENCE IF EXISTS public.contractors_contractor_id_seq;
DROP TABLE IF EXISTS public.contractors;
DROP SEQUENCE IF EXISTS public.commission_levels_level_id_seq;
DROP TABLE IF EXISTS public.commission_levels;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: commission_levels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.commission_levels (
    level_id integer NOT NULL,
    level integer NOT NULL,
    percentage numeric(6,2) NOT NULL,
    description character varying(120),
    scheme character varying(20) DEFAULT 'client'::character varying NOT NULL
);


--
-- Name: commission_levels_level_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.commission_levels_level_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: commission_levels_level_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.commission_levels_level_id_seq OWNED BY public.commission_levels.level_id;


--
-- Name: contractors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractors (
    contractor_id integer NOT NULL,
    batch integer NOT NULL,
    member_referrer_id integer NOT NULL,
    company_name character varying(120) NOT NULL,
    company_address character varying(255),
    representative_name character varying(120),
    contact_no character varying(30),
    date_joined date
);


--
-- Name: contractors_contractor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contractors_contractor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contractors_contractor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contractors_contractor_id_seq OWNED BY public.contractors.contractor_id;


--
-- Name: member_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.member_ledger (
    ledger_id integer NOT NULL,
    member_id integer NOT NULL,
    batch_id integer,
    entry_id integer,
    billing_date date NOT NULL,
    project_id integer,
    billing_id integer,
    project_title character varying(200),
    recipient_type character varying(20) NOT NULL,
    share_scheme character varying(40),
    level integer,
    share_amount numeric(14,2) NOT NULL,
    description character varying(255),
    created_at timestamp without time zone NOT NULL,
    transaction_type character varying(10) DEFAULT 'credit'::character varying NOT NULL,
    payout_request_id integer
);


--
-- Name: member_ledger_ledger_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.member_ledger_ledger_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: member_ledger_ledger_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.member_ledger_ledger_id_seq OWNED BY public.member_ledger.ledger_id;


--
-- Name: members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.members (
    member_id integer NOT NULL,
    batch integer NOT NULL,
    referrer_id integer,
    last_name character varying(80) NOT NULL,
    first_name character varying(80) NOT NULL,
    middle_name character varying(80),
    suffix character varying(20),
    address character varying(255),
    membership_type character varying(30),
    phone character varying(30),
    email character varying(120),
    birth_date date,
    gender character varying(20),
    civil_status character varying(30),
    highest_education character varying(80),
    occupation_income_source character varying(120),
    monthly_income character varying(40),
    number_of_dependents integer,
    beneficiary_name character varying(120),
    beneficiary_address character varying(255),
    beneficiary_phone character varying(30),
    status character varying(20) DEFAULT 'Active'::character varying,
    termination_date date,
    termination_type character varying(60),
    date_joined date,
    lifetime_cap_enabled boolean DEFAULT true,
    lifetime_cap_amount numeric(14,2) DEFAULT 50000000
);


--
-- Name: members_member_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.members_member_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: members_member_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.members_member_id_seq OWNED BY public.members.member_id;


--
-- Name: ompd_fund_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ompd_fund_entries (
    entry_id integer NOT NULL,
    payout_id integer NOT NULL,
    member_id integer NOT NULL,
    gross_amount numeric(14,2) NOT NULL,
    deduction_amount numeric(14,2) NOT NULL,
    net_released numeric(14,2) NOT NULL,
    release_method character varying(40),
    release_reference character varying(120),
    recorded_at timestamp without time zone NOT NULL
);


--
-- Name: ompd_fund_entries_entry_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ompd_fund_entries_entry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ompd_fund_entries_entry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ompd_fund_entries_entry_id_seq OWNED BY public.ompd_fund_entries.entry_id;


--
-- Name: payout_notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payout_notifications (
    notification_id integer NOT NULL,
    payout_id integer NOT NULL,
    audience_role character varying(20),
    user_id integer,
    title character varying(120) NOT NULL,
    message text NOT NULL,
    is_read boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: payout_notifications_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payout_notifications_notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payout_notifications_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payout_notifications_notification_id_seq OWNED BY public.payout_notifications.notification_id;


--
-- Name: payout_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payout_requests (
    payout_id integer NOT NULL,
    member_id integer NOT NULL,
    requested_amount numeric(14,2) NOT NULL,
    status character varying(30) NOT NULL,
    member_note text,
    requested_at timestamp without time zone NOT NULL,
    requested_by_user_id integer NOT NULL,
    request_reviewed_at timestamp without time zone,
    request_reviewed_by_user_id integer,
    request_review_note text,
    release_method character varying(40),
    release_reference character varying(120),
    release_account_info character varying(255),
    release_notes text,
    release_submitted_at timestamp without time zone,
    release_submitted_by_user_id integer,
    release_approved_at timestamp without time zone,
    release_approved_by_user_id integer,
    released_at timestamp without time zone,
    rejected_at timestamp without time zone,
    rejected_by_user_id integer,
    rejection_reason text,
    ompd_deduction numeric(14,2) DEFAULT 0,
    net_release_amount numeric(14,2) DEFAULT 0
);


--
-- Name: payout_requests_payout_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payout_requests_payout_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payout_requests_payout_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payout_requests_payout_id_seq OWNED BY public.payout_requests.payout_id;


--
-- Name: project_billings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_billings (
    billing_id integer NOT NULL,
    project_id integer NOT NULL,
    billing_date date NOT NULL,
    billing_amount numeric(14,2) NOT NULL
);


--
-- Name: project_billings_billing_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_billings_billing_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_billings_billing_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_billings_billing_id_seq OWNED BY public.project_billings.billing_id;


--
-- Name: project_commissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_commissions (
    project_id integer NOT NULL,
    project_title character varying(200) NOT NULL,
    address character varying(255),
    contractor_id integer NOT NULL,
    client_referrer_id integer,
    contractor_referrer_id integer
);


--
-- Name: project_commissions_project_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_commissions_project_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_commissions_project_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_commissions_project_id_seq OWNED BY public.project_commissions.project_id;


--
-- Name: sharing_batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sharing_batches (
    batch_id integer NOT NULL,
    generated_at timestamp without time zone NOT NULL,
    project_count integer,
    total_commission numeric(14,2),
    total_shared numeric(14,2),
    commission_date date,
    total_pool numeric(14,2) DEFAULT 0,
    total_pop numeric(14,2) DEFAULT 0,
    total_admin numeric(14,2) DEFAULT 0,
    total_client_pool numeric(14,2) DEFAULT 0,
    total_contractor_pool numeric(14,2) DEFAULT 0
);


--
-- Name: sharing_batches_batch_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sharing_batches_batch_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sharing_batches_batch_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sharing_batches_batch_id_seq OWNED BY public.sharing_batches.batch_id;


--
-- Name: sharing_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sharing_entries (
    entry_id integer NOT NULL,
    batch_id integer NOT NULL,
    project_id integer NOT NULL,
    member_id integer,
    level integer NOT NULL,
    percentage numeric(6,2) NOT NULL,
    share_amount numeric(14,2) NOT NULL,
    recipient_type character varying(20) DEFAULT 'member'::character varying,
    recipient_label character varying(120),
    share_scheme character varying(40),
    billing_id integer
);


--
-- Name: sharing_entries_entry_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sharing_entries_entry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sharing_entries_entry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sharing_entries_entry_id_seq OWNED BY public.sharing_entries.entry_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(80) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(120),
    role character varying(20),
    status character varying(20),
    member_id integer
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: commission_levels level_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.commission_levels ALTER COLUMN level_id SET DEFAULT nextval('public.commission_levels_level_id_seq'::regclass);


--
-- Name: contractors contractor_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractors ALTER COLUMN contractor_id SET DEFAULT nextval('public.contractors_contractor_id_seq'::regclass);


--
-- Name: member_ledger ledger_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_ledger ALTER COLUMN ledger_id SET DEFAULT nextval('public.member_ledger_ledger_id_seq'::regclass);


--
-- Name: members member_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.members ALTER COLUMN member_id SET DEFAULT nextval('public.members_member_id_seq'::regclass);


--
-- Name: ompd_fund_entries entry_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ompd_fund_entries ALTER COLUMN entry_id SET DEFAULT nextval('public.ompd_fund_entries_entry_id_seq'::regclass);


--
-- Name: payout_notifications notification_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_notifications ALTER COLUMN notification_id SET DEFAULT nextval('public.payout_notifications_notification_id_seq'::regclass);


--
-- Name: payout_requests payout_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests ALTER COLUMN payout_id SET DEFAULT nextval('public.payout_requests_payout_id_seq'::regclass);


--
-- Name: project_billings billing_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_billings ALTER COLUMN billing_id SET DEFAULT nextval('public.project_billings_billing_id_seq'::regclass);


--
-- Name: project_commissions project_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_commissions ALTER COLUMN project_id SET DEFAULT nextval('public.project_commissions_project_id_seq'::regclass);


--
-- Name: sharing_batches batch_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharing_batches ALTER COLUMN batch_id SET DEFAULT nextval('public.sharing_batches_batch_id_seq'::regclass);


--
-- Name: sharing_entries entry_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharing_entries ALTER COLUMN entry_id SET DEFAULT nextval('public.sharing_entries_entry_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Data for Name: commission_levels; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.commission_levels (level_id, level, percentage, description, scheme) FROM stdin;
1	1	50.00	Project client referrer	client
2	2	12.00	Upline 1	client
3	3	10.00	Upline 2	client
4	4	8.00	Upline 3	client
5	5	8.00	Upline 4	client
6	6	6.00	Upline 5	client
8	1	50.00	Contractor member referrer	contractor
9	2	12.00	Upline 1	contractor
10	3	10.00	Upline 2	contractor
11	4	8.00	Upline 3	contractor
12	5	8.00	Upline 4	contractor
13	6	6.00	Upline 5	contractor
7	7	6.00	Mandate account (Level 7)	client
14	7	6.00	Mandate account (Level 7)	contractor
\.


--
-- Data for Name: contractors; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.contractors (contractor_id, batch, member_referrer_id, company_name, company_address, representative_name, contact_no, date_joined) FROM stdin;
1001	1	3001	JJS BUILDERS	\N	\N	\N	\N
1002	1	3002	YY BUILDERS	\N	\N	\N	\N
\.


--
-- Data for Name: member_ledger; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.member_ledger (ledger_id, member_id, batch_id, entry_id, billing_date, project_id, billing_id, project_title, recipient_type, share_scheme, level, share_amount, description, created_at, transaction_type, payout_request_id) FROM stdin;
48	7001	8	120	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_client	1	15000.00	Platform Ref-Client — Level 1 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
49	6001	8	121	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_client	2	3600.00	Platform Ref-Client — Level 2 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
50	5001	8	122	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_client	3	3000.00	Platform Ref-Client — Level 3 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
51	4001	8	123	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_client	4	2400.00	Platform Ref-Client — Level 4 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
52	3001	8	124	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_client	5	2400.00	Platform Ref-Client — Level 5 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
53	2001	8	125	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_client	6	1800.00	Platform Ref-Client — Level 6 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
54	3002	8	127	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_contractor	1	10000.00	Platform Ref-Contractor — Level 1 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
55	2002	8	128	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_contractor	2	2400.00	Platform Ref-Contractor — Level 2 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
56	1002	8	129	2026-07-04	2	2	LEGAZPI CITY MPCC	member	platform_ref_contractor	3	2000.00	Platform Ref-Contractor — Level 3 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
57	7001	8	132	2026-07-04	2	2	LEGAZPI CITY MPCC	member	client	1	250000.00	Ref-Client — Level 1 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
58	6001	8	133	2026-07-04	2	2	LEGAZPI CITY MPCC	member	client	2	60000.00	Ref-Client — Level 2 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
59	5001	8	134	2026-07-04	2	2	LEGAZPI CITY MPCC	member	client	3	50000.00	Ref-Client — Level 3 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
60	4001	8	135	2026-07-04	2	2	LEGAZPI CITY MPCC	member	client	4	40000.00	Ref-Client — Level 4 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
61	3001	8	136	2026-07-04	2	2	LEGAZPI CITY MPCC	member	client	5	40000.00	Ref-Client — Level 5 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
62	2001	8	137	2026-07-04	2	2	LEGAZPI CITY MPCC	member	client	6	30000.00	Ref-Client — Level 6 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
63	3002	8	139	2026-07-04	2	2	LEGAZPI CITY MPCC	member	contractor	1	125000.00	Ref-Contractor — Level 1 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
64	2002	8	140	2026-07-04	2	2	LEGAZPI CITY MPCC	member	contractor	2	30000.00	Ref-Contractor — Level 2 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
65	1002	8	141	2026-07-04	2	2	LEGAZPI CITY MPCC	member	contractor	3	25000.00	Ref-Contractor — Level 3 — LEGAZPI CITY MPCC	2026-07-04 09:30:11.38299	credit	\N
\.


--
-- Data for Name: members; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.members (member_id, batch, referrer_id, last_name, first_name, middle_name, suffix, address, membership_type, phone, email, birth_date, gender, civil_status, highest_education, occupation_income_source, monthly_income, number_of_dependents, beneficiary_name, beneficiary_address, beneficiary_phone, status, termination_date, termination_type, date_joined, lifetime_cap_enabled, lifetime_cap_amount) FROM stdin;
1001	1	\N	DORIS	MA'AM	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
1002	1	\N	CATHY	MA'AM	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
2001	2	1001	GISELLE	MA'AM	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
3001	3	2001	NOLDIN	SIR	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
4001	4	3001	CLETUS	SIR	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
5001	5	4001	CONNIE	MA'AM	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
6001	6	5001	VICTOR	SIR	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
7001	7	6001	ANTHONY	SIR	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
8001	8	7001	JOHN	SIR	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
9001	9	8001	MARY	MA'AM	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
10001	10	9001	SHERYLL	MA'AM	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
2002	2	1002	CHE-CHE	MA'AM	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
3002	3	2002	PAUL	SIR	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	Active	\N	\N	\N	t	50000000.00
\.


--
-- Data for Name: ompd_fund_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ompd_fund_entries (entry_id, payout_id, member_id, gross_amount, deduction_amount, net_released, release_method, release_reference, recorded_at) FROM stdin;
\.


--
-- Data for Name: payout_notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payout_notifications (notification_id, payout_id, audience_role, user_id, title, message, is_read, created_at) FROM stdin;
\.


--
-- Data for Name: payout_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payout_requests (payout_id, member_id, requested_amount, status, member_note, requested_at, requested_by_user_id, request_reviewed_at, request_reviewed_by_user_id, request_review_note, release_method, release_reference, release_account_info, release_notes, release_submitted_at, release_submitted_by_user_id, release_approved_at, release_approved_by_user_id, released_at, rejected_at, rejected_by_user_id, rejection_reason, ompd_deduction, net_release_amount) FROM stdin;
\.


--
-- Data for Name: project_billings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project_billings (billing_id, project_id, billing_date, billing_amount) FROM stdin;
2	2	2026-07-04	1000000.00
\.


--
-- Data for Name: project_commissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project_commissions (project_id, project_title, address, contractor_id, client_referrer_id, contractor_referrer_id) FROM stdin;
2	LEGAZPI CITY MPCC	\N	1002	7001	3002
\.


--
-- Data for Name: sharing_batches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sharing_batches (batch_id, generated_at, project_count, total_commission, total_shared, commission_date, total_pool, total_pop, total_admin, total_client_pool, total_contractor_pool) FROM stdin;
8	2026-07-04 09:30:11.38299	1	1000000.00	692600.00	2026-07-04	750000.00	84400.00	0.00	500000.00	250000.00
\.


--
-- Data for Name: sharing_entries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sharing_entries (entry_id, batch_id, project_id, member_id, level, percentage, share_amount, recipient_type, recipient_label, share_scheme, billing_id) FROM stdin;
119	8	2	\N	0	10.00	25000.00	pop	Poorest of the Poor (POP) (Platform)	platform_pop	2
120	8	2	7001	1	50.00	15000.00	member	\N	platform_ref_client	2
121	8	2	6001	2	12.00	3600.00	member	\N	platform_ref_client	2
122	8	2	5001	3	10.00	3000.00	member	\N	platform_ref_client	2
123	8	2	4001	4	8.00	2400.00	member	\N	platform_ref_client	2
124	8	2	3001	5	8.00	2400.00	member	\N	platform_ref_client	2
125	8	2	2001	6	6.00	1800.00	member	\N	platform_ref_client	2
126	8	2	\N	7	6.00	1800.00	mandate	Mandate Account (Platform Ref-Client)	platform_ref_client	2
127	8	2	3002	1	50.00	10000.00	member	\N	platform_ref_contractor	2
128	8	2	2002	2	12.00	2400.00	member	\N	platform_ref_contractor	2
129	8	2	1002	3	10.00	2000.00	member	\N	platform_ref_contractor	2
130	8	2	\N	7	6.00	1200.00	mandate	Mandate Account (Platform Ref-Contractor)	platform_ref_contractor	2
131	8	2	\N	0	22.00	4400.00	pop	Poorest of the Poor (POP) (Ref-Contractor)	platform_ref_contractor	2
132	8	2	7001	1	50.00	250000.00	member	\N	client	2
133	8	2	6001	2	12.00	60000.00	member	\N	client	2
134	8	2	5001	3	10.00	50000.00	member	\N	client	2
135	8	2	4001	4	8.00	40000.00	member	\N	client	2
136	8	2	3001	5	8.00	40000.00	member	\N	client	2
137	8	2	2001	6	6.00	30000.00	member	\N	client	2
138	8	2	\N	7	6.00	30000.00	mandate	Mandate Account (Ref-Client)	client	2
139	8	2	3002	1	50.00	125000.00	member	\N	contractor	2
140	8	2	2002	2	12.00	30000.00	member	\N	contractor	2
141	8	2	1002	3	10.00	25000.00	member	\N	contractor	2
142	8	2	\N	7	6.00	15000.00	mandate	Mandate Account (Ref-Contractor)	contractor	2
143	8	2	\N	0	22.00	55000.00	pop	Poorest of the Poor (POP) (Ref-Contractor)	contractor	2
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (user_id, username, password_hash, full_name, role, status, member_id) FROM stdin;
1	Admin	scrypt:32768:8:1$1aylCjxMCEUns7kS$eeb7c481374d40a523ae478db806c03b8111ac0e37aa3f8ab53995831904c81573719bd397cde7a51c83108cc93d946ed31dcd1cf34f1c55e076cd0058fcf5d0	System Administrator	Admin	Active	\N
3	Cletus	scrypt:32768:8:1$mrs1Q8EMi9HTgldl$75a1a984d801d7a4aa02dd7052283fc537f80e332373294b0ce409f27e9452f2f799aad8169309882d094890f2ecf4e634ae19715db00db9b74cb6ef53bec7de	Cletus Caido	Member	Active	4001
5	Giselle	scrypt:32768:8:1$gkFrkLLxRKEbhDNi$cf5a4445e6fb380470a3447150e8861501348ad3f5c3cd1820ebcb92f1b88c5be4b18aa49bb686727919a17949e9f9d0aee87c645fbe99a7d0d509cb84d538ae	Ma'am Giselle	Staff	Active	\N
4	PortalAdmin	scrypt:32768:8:1$KOnSyDtpFexLUzdR$bf73713c99614a001ac3dd0702a101ac641f84914634cadbd8e8f7821d88f119e62114f205f0e63d501e994b7900cbc6ac98269d01809885eae865b0e18c2883	Portal Administrator	PortalAdmin	Active	\N
\.


--
-- Name: commission_levels_level_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.commission_levels_level_id_seq', 14, true);


--
-- Name: contractors_contractor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.contractors_contractor_id_seq', 1, false);


--
-- Name: member_ledger_ledger_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.member_ledger_ledger_id_seq', 65, true);


--
-- Name: members_member_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.members_member_id_seq', 1, false);


--
-- Name: ompd_fund_entries_entry_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.ompd_fund_entries_entry_id_seq', 3, true);


--
-- Name: payout_notifications_notification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.payout_notifications_notification_id_seq', 20, true);


--
-- Name: payout_requests_payout_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.payout_requests_payout_id_seq', 4, true);


--
-- Name: project_billings_billing_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.project_billings_billing_id_seq', 2, true);


--
-- Name: project_commissions_project_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.project_commissions_project_id_seq', 2, true);


--
-- Name: sharing_batches_batch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sharing_batches_batch_id_seq', 8, true);


--
-- Name: sharing_entries_entry_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sharing_entries_entry_id_seq', 143, true);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_user_id_seq', 5, true);


--
-- Name: commission_levels commission_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.commission_levels
    ADD CONSTRAINT commission_levels_pkey PRIMARY KEY (level_id);


--
-- Name: contractors contractors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT contractors_pkey PRIMARY KEY (contractor_id);


--
-- Name: member_ledger member_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_ledger
    ADD CONSTRAINT member_ledger_pkey PRIMARY KEY (ledger_id);


--
-- Name: members members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.members
    ADD CONSTRAINT members_pkey PRIMARY KEY (member_id);


--
-- Name: ompd_fund_entries ompd_fund_entries_payout_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ompd_fund_entries
    ADD CONSTRAINT ompd_fund_entries_payout_id_key UNIQUE (payout_id);


--
-- Name: ompd_fund_entries ompd_fund_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ompd_fund_entries
    ADD CONSTRAINT ompd_fund_entries_pkey PRIMARY KEY (entry_id);


--
-- Name: payout_notifications payout_notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_notifications
    ADD CONSTRAINT payout_notifications_pkey PRIMARY KEY (notification_id);


--
-- Name: payout_requests payout_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_pkey PRIMARY KEY (payout_id);


--
-- Name: project_billings project_billings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_billings
    ADD CONSTRAINT project_billings_pkey PRIMARY KEY (billing_id);


--
-- Name: project_commissions project_commissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_commissions
    ADD CONSTRAINT project_commissions_pkey PRIMARY KEY (project_id);


--
-- Name: sharing_batches sharing_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharing_batches
    ADD CONSTRAINT sharing_batches_pkey PRIMARY KEY (batch_id);


--
-- Name: sharing_entries sharing_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharing_entries
    ADD CONSTRAINT sharing_entries_pkey PRIMARY KEY (entry_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: uq_commission_levels_scheme_level; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_commission_levels_scheme_level ON public.commission_levels USING btree (scheme, level);


--
-- Name: contractors contractors_member_referrer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT contractors_member_referrer_id_fkey FOREIGN KEY (member_referrer_id) REFERENCES public.members(member_id);


--
-- Name: member_ledger member_ledger_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_ledger
    ADD CONSTRAINT member_ledger_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.sharing_batches(batch_id);


--
-- Name: member_ledger member_ledger_billing_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_ledger
    ADD CONSTRAINT member_ledger_billing_id_fkey FOREIGN KEY (billing_id) REFERENCES public.project_billings(billing_id);


--
-- Name: member_ledger member_ledger_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_ledger
    ADD CONSTRAINT member_ledger_entry_id_fkey FOREIGN KEY (entry_id) REFERENCES public.sharing_entries(entry_id);


--
-- Name: member_ledger member_ledger_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_ledger
    ADD CONSTRAINT member_ledger_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(member_id);


--
-- Name: member_ledger member_ledger_payout_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_ledger
    ADD CONSTRAINT member_ledger_payout_request_id_fkey FOREIGN KEY (payout_request_id) REFERENCES public.payout_requests(payout_id);


--
-- Name: member_ledger member_ledger_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.member_ledger
    ADD CONSTRAINT member_ledger_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project_commissions(project_id);


--
-- Name: members members_referrer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.members
    ADD CONSTRAINT members_referrer_id_fkey FOREIGN KEY (referrer_id) REFERENCES public.members(member_id);


--
-- Name: ompd_fund_entries ompd_fund_entries_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ompd_fund_entries
    ADD CONSTRAINT ompd_fund_entries_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(member_id);


--
-- Name: ompd_fund_entries ompd_fund_entries_payout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ompd_fund_entries
    ADD CONSTRAINT ompd_fund_entries_payout_id_fkey FOREIGN KEY (payout_id) REFERENCES public.payout_requests(payout_id);


--
-- Name: payout_notifications payout_notifications_payout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_notifications
    ADD CONSTRAINT payout_notifications_payout_id_fkey FOREIGN KEY (payout_id) REFERENCES public.payout_requests(payout_id);


--
-- Name: payout_notifications payout_notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_notifications
    ADD CONSTRAINT payout_notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: payout_requests payout_requests_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(member_id);


--
-- Name: payout_requests payout_requests_rejected_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_rejected_by_user_id_fkey FOREIGN KEY (rejected_by_user_id) REFERENCES public.users(user_id);


--
-- Name: payout_requests payout_requests_release_approved_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_release_approved_by_user_id_fkey FOREIGN KEY (release_approved_by_user_id) REFERENCES public.users(user_id);


--
-- Name: payout_requests payout_requests_release_submitted_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_release_submitted_by_user_id_fkey FOREIGN KEY (release_submitted_by_user_id) REFERENCES public.users(user_id);


--
-- Name: payout_requests payout_requests_request_reviewed_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_request_reviewed_by_user_id_fkey FOREIGN KEY (request_reviewed_by_user_id) REFERENCES public.users(user_id);


--
-- Name: payout_requests payout_requests_requested_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payout_requests
    ADD CONSTRAINT payout_requests_requested_by_user_id_fkey FOREIGN KEY (requested_by_user_id) REFERENCES public.users(user_id);


--
-- Name: project_billings project_billings_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_billings
    ADD CONSTRAINT project_billings_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project_commissions(project_id);


--
-- Name: project_commissions project_commissions_client_referrer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_commissions
    ADD CONSTRAINT project_commissions_client_referrer_id_fkey FOREIGN KEY (client_referrer_id) REFERENCES public.members(member_id);


--
-- Name: project_commissions project_commissions_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_commissions
    ADD CONSTRAINT project_commissions_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.contractors(contractor_id);


--
-- Name: project_commissions project_commissions_contractor_referrer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_commissions
    ADD CONSTRAINT project_commissions_contractor_referrer_id_fkey FOREIGN KEY (contractor_referrer_id) REFERENCES public.members(member_id);


--
-- Name: sharing_entries sharing_entries_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharing_entries
    ADD CONSTRAINT sharing_entries_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.sharing_batches(batch_id);


--
-- Name: sharing_entries sharing_entries_billing_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharing_entries
    ADD CONSTRAINT sharing_entries_billing_id_fkey FOREIGN KEY (billing_id) REFERENCES public.project_billings(billing_id);


--
-- Name: sharing_entries sharing_entries_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharing_entries
    ADD CONSTRAINT sharing_entries_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(member_id);


--
-- Name: sharing_entries sharing_entries_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharing_entries
    ADD CONSTRAINT sharing_entries_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project_commissions(project_id);


--
-- Name: users users_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(member_id);


--
-- PostgreSQL database dump complete
--

\unrestrict 2Evxpig4Zmz10ktRzr0m0lKKUziQGwxTT4yughFZkRYlQhevxFdSU1ivNetfqK1

