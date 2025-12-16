<script setup>
import { RouterLink } from "vue-router"
import {
  HomeIcon,
  CubeIcon,
  BeakerIcon,
  AcademicCapIcon,
  BuildingOffice2Icon
} from "@heroicons/vue/24/outline"
</script>

<template>
  <nav class="navbar">
    <img src="@/assets/logo2.png" height="50" />
    <div class="main-title" >AUTO PILOT </div>

    <ul class="menu">
      <li>
        <RouterLink to="/" exact-active-class="active">
          <HomeIcon class="icon" />
          Dashboard
        </RouterLink>
      </li>
      <li>
        <RouterLink to="/parts" active-class="active">
          <CubeIcon class="icon" />
          Parts
        </RouterLink>
      </li>
      <li>
        <RouterLink to="/steps" active-class="active">
          <BeakerIcon class="icon" />
          Step Analyse
        </RouterLink>
      </li>
      <li>
        <RouterLink to="/machines" active-class="active">
          <BuildingOffice2Icon class="icon" />
          Machine Report
        </RouterLink>
      </li>
        <li>
        <RouterLink to="/chatIA" active-class="active">
          <AcademicCapIcon class="icon" />
          Chat IA
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>



<style scoped>
.navbar {
  height: 60px;
  color: white;
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.main-title {
  font-weight: bold;
  margin-right: 40px;
  margin-left: 20px;
}

.menu {
  display: flex;
  gap: 20px;
  list-style: none;
}

a {
  color: #cbd5f5;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 6px;
}

a:hover {
  background: #1e293b;
}

.active {
  background: #1e293b;
  color: white;
}

.menu a {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e6edf3;
}

.icon {
  width: 20px;
  height: 20px;
  color: #ffffff;
}

.active .icon {
  color: #ffffff;
}
</style>
