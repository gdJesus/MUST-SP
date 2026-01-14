import sqlite3
import pyodbc

from pathlib import Path
from datetime import datetime


# ==============================================================================
# MODELO DE DADOS (DATABASE)
# ==============================================================================

class DashboardDB:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Arquivo de banco de dados não encontrado: {self.db_path}")

        self.db_type = 'access' if self.db_path.suffix.lower() == '.accdb' else 'sqlite'
        
        if self.db_type == 'sqlite':
            self.tbl_empresas = 'empresas'
            self.tbl_anotacao = 'anotacao'
            self.tbl_valores = 'valores_must'
        else:
            self.tbl_empresas = 'tb_empresas'
            self.tbl_anotacao = 'tb_anotacao'
            self.tbl_valores = 'tb_valores_must'

        if self.db_type == 'sqlite':
            self._ensure_approval_columns_exist_sqlite()

        self.company_links = {
            'SUL SUDESTE': 'https://onsbr-my.sharepoint.com/:b:/g/personal/pedrovictor_veras_ons_org_br/EbWWq1r7MnxPvOejycbr82cB5a_rN_PCsDMDjp9r3bF3Ng?e=C7dxKN',
            'ELETROPAULO': 'https://onsbr-my.sharepoint.com/:b:/g/personal/pedrovictor_veras_ons_org_br/EXzdo_ClziVDrnOHTiGzoysBdqgci92tpuKYN2xKIjPQvw?e=kzrFho',
            'PIRATININGA': 'https://onsbr-my.sharepoint.com/:b:/g/personal/pedrovictor_veras_ons_org_br/EZGF1uzc1opGujAlp1fwNqcBoLnXsAt532XFPbNrNCwEvQ?e=nEOCn9',
            'NEOENERGIA ELEKTRO': 'https://onsbr-my.sharepoint.com/:b:/g/personal/pedrovictor_veras_ons_org_br/Eet4gEXFfDNEoPMejiLnMaQBVW1ubN1TxOIvMtLY0yUfPA?e=WruSdk',
            'JAGUARI': 'https://onsbr-my.sharepoint.com/:b:/g/personal/pedrovictor_veras_ons_org_br/EXzdo_ClziVDrnOHTiGzoysBdqgci92tpuKYN2xKIjPQvw?e=b2yXV2',
            'CPFL PAULISTA': 'https://onsbr-my.sharepoint.com/:b:/g/personal/pedrovictor_veras_ons_org_br/EbWWq1r7MnxPvOejycbr82cB5a_rN_PCsDMDjp9r3bF3Ng?e=C7dxKN'
        }

    def _get_connection(self):
        if self.db_type == 'sqlite':
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        else:
            conn_str = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};" fr"DBQ={self.db_path};")
            return pyodbc.connect(conn_str)

    def _execute_query(self, query, params=(), fetch_one=False):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                columns = [column[0] for column in cursor.description]
                if fetch_one:
                    result = cursor.fetchone()
                    return dict(zip(columns, result)) if result else None
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except (sqlite3.Error, pyodbc.Error) as e:
            print(f"Erro de banco de dados (leitura): {e}")
            return [] if not fetch_one else None

    def _execute_write_query(self, query, params=()):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
            return True
        except (sqlite3.Error, pyodbc.Error) as e:
            print(f"Erro de banco de dados (escrita): {e}")
            return False

    def _ensure_approval_columns_exist_sqlite(self):
        try:
            table_info = self._execute_query(f"PRAGMA table_info({self.tbl_anotacao})")
            column_names = [col['name'] for col in table_info]
            if 'aprovado_por' not in column_names:
                self._execute_write_query(f"ALTER TABLE {self.tbl_anotacao} ADD COLUMN aprovado_por TEXT;")
            if 'data_aprovacao' not in column_names:
                self._execute_write_query(f"ALTER TABLE {self.tbl_anotacao} ADD COLUMN data_aprovacao TEXT;")
        except Exception as e:
            print(f"Erro ao verificar tabela '{self.tbl_anotacao}': {e}")
            
    def get_kpi_summary(self):
        query_companies = f"SELECT COUNT(*) as count FROM {self.tbl_empresas};"
        query_points = f"SELECT COUNT(*) as count FROM {self.tbl_anotacao};"
        query_remarks = f"SELECT COUNT(*) as count FROM {self.tbl_anotacao} WHERE anotacao_geral IS NOT NULL AND anotacao_geral <> '' AND anotacao_geral <> 'nan';"
        try:
            total_companies = self._execute_query(query_companies, fetch_one=True)['count']
            total_points = self._execute_query(query_points, fetch_one=True)['count']
            points_with_remarks = self._execute_query(query_remarks, fetch_one=True)['count']
            percentage = (points_with_remarks / total_points * 100) if total_points > 0 else 0
            return {
                'unique_companies': total_companies,
                'total_points': total_points,
                'points_with_remarks': points_with_remarks,
                'percentage_with_remarks': f"{percentage:.1f}%"
            }
        except (TypeError, KeyError, ZeroDivisionError) as e:
            print(f"Erro ao calcular KPIs: {e}")
            return {'unique_companies': 0, 'total_points': 0, 'points_with_remarks': 0, 'percentage_with_remarks': '0.0%'}

    def get_company_analysis(self):
        query = f"""
            SELECT e.nome_empresa, COUNT(a.id_conexao) as total,
                   SUM(IIF(a.anotacao_geral IS NOT NULL AND a.anotacao_geral <> '' AND a.anotacao_geral <> 'nan', 1, 0)) as with_remarks
            FROM {self.tbl_empresas} AS e INNER JOIN {self.tbl_anotacao} AS a ON e.id_empresa = a.id_empresa
            GROUP BY e.nome_empresa ORDER BY e.nome_empresa;
        """
        return self._execute_query(query)
        
    def get_yearly_must_stats(self):
        query = f"SELECT ano, periodo, SUM(valor) as total_valor FROM {self.tbl_valores} GROUP BY ano, periodo ORDER BY ano, periodo;"
        return self._execute_query(query)

    def get_unique_companies(self):
        query = f"SELECT nome_empresa FROM {self.tbl_empresas} ORDER BY nome_empresa;"
        return [row['nome_empresa'] for row in self._execute_query(query)]

    def get_unique_tensions(self):
        query = f"SELECT DISTINCT tensao_kv FROM {self.tbl_anotacao} WHERE tensao_kv IS NOT NULL ORDER BY tensao_kv;"
        return [str(row['tensao_kv']) for row in self._execute_query(query)]

    def get_all_connection_points(self, filters=None):
        query = f"""
            SELECT emp.nome_empresa, a.cod_ons, a.tensao_kv, a.anotacao_geral, a.aprovado_por, a.data_aprovacao
            FROM ({self.tbl_empresas} AS emp
            INNER JOIN {self.tbl_anotacao} AS a ON emp.id_empresa = a.id_empresa)
        """
        conditions, params = [], []
        if filters:
            year_filter = filters.get("year")
            if year_filter and year_filter != "Todos":
                conditions.append(f"a.id_conexao IN (SELECT vm.id_conexao FROM {self.tbl_valores} vm WHERE vm.ano = ?)")
                params.append(int(year_filter))
            if filters.get("company") and filters["company"] != "Todas":
                conditions.append("emp.nome_empresa = ?")
                params.append(filters["company"])
            if filters.get("search"):
                search_term = f"%{filters['search']}%"
                conditions.append("(a.cod_ons LIKE ? OR a.anotacao_geral LIKE ?)")
                params.extend([search_term, search_term])
            if filters.get("tension") and filters["tension"] != "Todas":
                conditions.append("a.tensao_kv = ?")
                params.append(int(filters["tension"]))
            if filters.get("status") == "Com Ressalva":
                conditions.append("(a.anotacao_geral IS NOT NULL AND a.anotacao_geral <> '' AND a.anotacao_geral <> 'nan')")
            elif filters.get("status") == "Aprovado":
                conditions.append("(a.aprovado_por IS NOT NULL AND a.aprovado_por <> '')")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY emp.nome_empresa, a.cod_ons;"
        
        results = self._execute_query(query, tuple(params))
        for row in results:
            normalized_empresa = str(row['nome_empresa']).strip().upper()
            row['arquivo_referencia'] = self.company_links.get(normalized_empresa, '')
        return results

    def get_must_history_for_point(self, cod_ons):
        query = f"""
            SELECT vm.ano, vm.periodo, vm.valor
            FROM {self.tbl_valores} AS vm
            INNER JOIN {self.tbl_anotacao} AS a ON vm.id_conexao = a.id_conexao
            WHERE a.cod_ons = ? ORDER BY vm.ano, vm.periodo;
        """
        return self._execute_query(query, (cod_ons,))

    def approve_point(self, cod_ons, approver_name):
        query = f"UPDATE {self.tbl_anotacao} SET aprovado_por = ?, data_aprovacao = ? WHERE cod_ons = ?;"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._execute_write_query(query, (approver_name, timestamp, cod_ons))
        
    def get_data_for_charts(self):
        points_per_company_query = f"SELECT e.nome_empresa, COUNT(a.id_conexao) as count FROM {self.tbl_empresas} AS e INNER JOIN {self.tbl_anotacao} AS a ON e.id_empresa = a.id_empresa GROUP BY e.nome_empresa"
        remarks_summary_query = f"SELECT SUM(IIF(anotacao_geral IS NOT NULL AND anotacao_geral <> '' AND anotacao_geral <> 'nan', 1, 0)) as with_remarks, COUNT(id_conexao) as total FROM {self.tbl_anotacao}"
        yearly_sum_query = f"SELECT ano, SUM(valor) as total_valor FROM {self.tbl_valores} GROUP BY ano ORDER BY ano"
        return {
            "points_per_company": self._execute_query(points_per_company_query),
            "remarks_summary": self._execute_query(remarks_summary_query, fetch_one=True),
            "yearly_sum": self._execute_query(yearly_sum_query),
        }

